// GENERIC NODE FINDER SCRIPT
// =========================
// Purpose: Find and display complete JSON snippets for any specified scene or quest node type
// Configurable: Node type, result limits, file limits, and output format
// =========================

// @author MisterChedda
// @version 0.1

import * as Logger from 'Logger.wscript';
import * as TypeHelper from 'TypeHelper.wscript';

// ===== CONFIGURATION SECTION =====
// Change these values to customize the search

// TARGET NODE TYPE - Change this to search for different node types
const TARGET_NODE_TYPE = "scnXorNode";        // Examples: "scnXorNode", "scnSectionNode", "scnStartNode", "scnEndNode", "questFlowControlNodeDefinition"

// RESULT LIMITS
const MAX_RESULTS = 10;                         // Maximum number of results to display
const MAX_FILES_TO_PROCESS = 2000;             // Maximum files to scan (set to 99999 for unlimited)
const MAX_NODES_PER_FILE = 150;                // Skip files with more than this many nodes (to help target simpler scenes/questphase)

// FILE TYPE SELECTION
const INCLUDE_SCENE = true;                     // Include .scene files
const INCLUDE_QUESTPHASE = false;                // Include .questphase files

// PROGRESS REPORTING
const PROGRESS_INTERVAL = 100;                 // Show progress every N files
const SHOW_DETAILED_PROGRESS = true;           // Show detailed progress info

// OUTPUT OPTIONS
const SAVE_RESULTS = true;                      // Save results to file
const SHOW_FULL_JSON = false;                   // Show complete JSON or just key properties

// ===== MAIN FUNCTION =====
function main() {
    Logger.Info("=== GENERIC NODE FINDER ===");
    Logger.Info(`Searching for node type: ${TARGET_NODE_TYPE}`);
    Logger.Info(`Max results: ${MAX_RESULTS}`);
    Logger.Info(`Max files to process: ${MAX_FILES_TO_PROCESS}`);
    Logger.Info(`Include .scene files: ${INCLUDE_SCENE}`);
    Logger.Info(`Include .questphase files: ${INCLUDE_QUESTPHASE}`);
    
    const state = initializeState();
    
    try {
        // Phase 1: Collect target files
        Logger.Info("Phase 1: Collecting target files...");
        collectTargetFiles(state);
        
        if (state.targetFiles.length === 0) {
            Logger.Warning("No target files found!");
            return;
        }
        
        Logger.Info(`Found ${state.targetFiles.length} files to analyze`);
        
        // Phase 2: Search for target nodes
        Logger.Info("Phase 2: Searching for target nodes...");
        searchForNodes(state);
        
        // Phase 3: Display and save results
        Logger.Info("Phase 3: Displaying and saving results...");
        displayResults(state);
        
        Logger.Info("=== Node search completed! ===");
        
    } catch (error) {
        Logger.Error("Fatal error during node search: " + error.message);
        wkit.ShowMessageBox(
            "Node search failed with error:\n" + error.message,
            "Search Error", 2, 0
        );
    }
}

// ===== STATE INITIALIZATION =====
function initializeState() {
    return {
        targetFiles: [],
        processedFiles: 0,
        skippedFiles: 0,
        startTime: Date.now(),
        
        // Results tracking
        foundNodes: [],
        totalNodesFound: 0,
        filesWithTargetNodes: 0,
        
        // Output file names
        outputJson: `node_finder_${TARGET_NODE_TYPE}_${Date.now()}.json`,
        outputTxt: `node_finder_${TARGET_NODE_TYPE}_${Date.now()}.txt`,
        
        errors: []
    };
}

// ===== FILE COLLECTION =====
function collectTargetFiles(state) {
    Logger.Info("Scanning archives for target files...");
    
    const archiveFiles = wkit.GetArchiveFiles();
    let skippedVersions = 0;
    let collectedFiles = 0;
    
    for (const gameFile of archiveFiles) {
        if (!gameFile || !gameFile.FileName) continue;
        
        const fileName = gameFile.FileName.toLowerCase();
        
        // Skip version folders
        if (fileName.includes("versions")) {
            skippedVersions++;
            continue;
        }
        
        // Check file type inclusion
        const shouldInclude = 
            (INCLUDE_SCENE && fileName.endsWith('.scene')) ||
            (INCLUDE_QUESTPHASE && fileName.endsWith('.questphase'));
        
        if (shouldInclude) {
            state.targetFiles.push(gameFile);
            collectedFiles++;
            
            // Respect file limit
            if (collectedFiles >= MAX_FILES_TO_PROCESS) {
                Logger.Info(`Reached file limit of ${MAX_FILES_TO_PROCESS}, stopping collection`);
                break;
            }
        }
    }
    
    Logger.Info(`Collected ${collectedFiles} files for processing`);
    Logger.Info(`Skipped ${skippedVersions} files in version folders`);
}

// ===== NODE SEARCHING =====
function searchForNodes(state) {
    let processed = 0;
    
    for (const gameFile of state.targetFiles) {
        try {
            processed++;
            
            // Progress update
            if (processed % PROGRESS_INTERVAL === 0) {
                const elapsed = Math.round((Date.now() - state.startTime) / 1000);
                if (SHOW_DETAILED_PROGRESS) {
                    Logger.Info(`Progress: ${processed}/${state.targetFiles.length} files (${elapsed}s) | Found: ${state.totalNodesFound} nodes`);
                }
            }
            
            // Early exit if we have enough results
            if (state.foundNodes.length >= MAX_RESULTS) {
                Logger.Info("Reached maximum results limit, stopping search");
                break;
            }
            
            // Load and parse file
            const fileContent = wkit.GameFileToJson(gameFile);
            if (!fileContent) {
                state.errors.push(`Failed to load: ${gameFile.FileName}`);
                continue;
            }
            
            let parsedContent;
            try {
                parsedContent = TypeHelper.JsonParse(fileContent);
            } catch (parseError) {
                state.errors.push(`Failed to parse: ${gameFile.FileName}`);
                continue;
            }
            
            if (!parsedContent) continue;
            
            // Check node count and skip if file is too large
            const nodeCount = getNodeCount(parsedContent, gameFile.FileName);
            if (nodeCount > MAX_NODES_PER_FILE) {
                state.skippedFiles++;
                continue;
            }
            
            // Search for target nodes in this file
            const foundInFile = searchFileForTargetNodes(parsedContent, gameFile.FileName);
            
            if (foundInFile.length > 0) {
                state.filesWithTargetNodes++;
                state.totalNodesFound += foundInFile.length;
                
                // Add to results (respecting max results limit)
                for (const node of foundInFile) {
                    if (state.foundNodes.length < MAX_RESULTS) {
                        state.foundNodes.push(node);
                    }
                }
                
                Logger.Info(`Found ${foundInFile.length} ${TARGET_NODE_TYPE} nodes in ${gameFile.FileName}`);
            }
            
        } catch (error) {
            Logger.Error(`Error processing ${gameFile.FileName}: ${error.message}`);
            state.errors.push(`Error: ${gameFile.FileName} - ${error.message}`);
        }
    }
    
    state.processedFiles = processed;
}

// ===== SEARCH INDIVIDUAL FILE =====
function searchFileForTargetNodes(parsedContent, fileName) {
    const foundNodes = [];
    
    try {
        // Try scene file structure first
        const sceneGraph = parsedContent?.Data?.RootChunk?.sceneGraph?.Data?.graph;
        if (Array.isArray(sceneGraph)) {
            for (const nodeHandle of sceneGraph) {
                const nodeData = nodeHandle?.Data;
                if (nodeData && nodeData.$type === TARGET_NODE_TYPE) {
                    foundNodes.push(createNodeResult(nodeData, fileName, "scene"));
                }
            }
        }
        
        // Try quest file structure
        const questGraph = parsedContent?.Data?.RootChunk?.graph?.Data;
        if (questGraph) {
            const questNodes = questGraph.questNodes || questGraph.nodes || [];
            if (Array.isArray(questNodes)) {
                for (const nodeHandle of questNodes) {
                    const nodeData = nodeHandle?.Data;
                    if (nodeData && nodeData.$type === TARGET_NODE_TYPE) {
                        foundNodes.push(createNodeResult(nodeData, fileName, "quest"));
                    }
                }
            }
        }
        
    } catch (error) {
        Logger.Warning(`Error searching nodes in ${fileName}: ${error.message}`);
    }
    
    return foundNodes;
}

// ===== CREATE NODE RESULT =====
function createNodeResult(nodeData, fileName, fileType) {
    const nodeId = nodeData.nodeId?.id || nodeData.id || "unknown";
    
    return {
        fileName: fileName,
        fileType: fileType,
        nodeId: nodeId,
        nodeType: nodeData.$type,
        completeJson: SHOW_FULL_JSON ? JSON.stringify(nodeData, null, 2) : null,
        keyProperties: extractKeyProperties(nodeData),
        rawNodeData: nodeData // Keep reference for detailed analysis
    };
}

// ===== EXTRACT KEY PROPERTIES =====
function extractKeyProperties(nodeData) {
    const keyProps = {
        type: nodeData.$type,
        id: nodeData.nodeId?.id || nodeData.id || "unknown"
    };
    
    // Add common properties that might be interesting
    if (nodeData.name) keyProps.name = nodeData.name;
    if (nodeData.title) keyProps.title = nodeData.title;
    if (nodeData.description) keyProps.description = nodeData.description;
    if (nodeData.opensAt !== undefined) keyProps.opensAt = nodeData.opensAt;
    if (nodeData.closesAt !== undefined) keyProps.closesAt = nodeData.closesAt;
    if (nodeData.isOpen !== undefined) keyProps.isOpen = nodeData.isOpen;
    if (nodeData.inputSockets) keyProps.inputSocketCount = nodeData.inputSockets.length;
    if (nodeData.outputSockets) keyProps.outputSocketCount = nodeData.outputSockets.length;
    
    return keyProps;
}

// ===== NODE COUNT HELPER =====
function getNodeCount(parsedContent, fileName) {
    try {
        // Try scene file structure
        const sceneGraph = parsedContent?.Data?.RootChunk?.sceneGraph?.Data?.graph;
        if (Array.isArray(sceneGraph)) {
            return sceneGraph.length;
        }
        
        // Try quest file structure
        const questGraph = parsedContent?.Data?.RootChunk?.graph?.Data;
        if (questGraph) {
            const questNodes = questGraph.questNodes || questGraph.nodes || [];
            if (Array.isArray(questNodes)) {
                return questNodes.length;
            }
        }
        
        return 0;
    } catch (error) {
        Logger.Warning(`Error counting nodes in ${fileName}: ${error.message}`);
        return 0;
    }
}

// ===== DISPLAY RESULTS =====
function displayResults(state) {
    const duration = Math.round((Date.now() - state.startTime) / 1000);
    
    Logger.Info("=== SEARCH RESULTS ===");
    Logger.Info(`Files processed: ${state.processedFiles}`);
    Logger.Info(`Files skipped (too large): ${state.skippedFiles}`);
    Logger.Info(`Files with target nodes: ${state.filesWithTargetNodes}`);
    Logger.Info(`Total nodes found: ${state.totalNodesFound}`);
    Logger.Info(`Showing first ${state.foundNodes.length} results`);
    Logger.Info(`Duration: ${duration} seconds`);
    
    Logger.Info("\n=== NODE DETAILS ===");
    
    for (let i = 0; i < state.foundNodes.length; i++) {
        const node = state.foundNodes[i];
        
        Logger.Info(`\n--- Result ${i + 1} ---`);
        Logger.Info(`File: ${node.fileName}`);
        Logger.Info(`Node ID: ${node.nodeId}`);
        Logger.Info(`Node Type: ${node.nodeType}`);
        Logger.Info(`File Type: ${node.fileType}`);
        
        if (SHOW_FULL_JSON && node.completeJson) {
            Logger.Info(`Complete JSON:\n${node.completeJson}`);
        } else {
            Logger.Info(`Key Properties: ${JSON.stringify(node.keyProperties, null, 2)}`);
        }
    }
    
    // Save results if enabled
    if (SAVE_RESULTS) {
        saveResults(state, duration);
    }
    
    // Show completion dialog
    showCompletionDialog(state, duration);
}

// ===== SAVE RESULTS =====
function saveResults(state, duration) {
    try {
        // Save JSON data
        const jsonData = {
            metadata: {
                searchDate: new Date().toISOString(),
                targetNodeType: TARGET_NODE_TYPE,
                filesProcessed: state.processedFiles,
                totalNodesFound: state.totalNodesFound,
                resultsShown: state.foundNodes.length,
                duration: duration
            },
            results: state.foundNodes,
            errors: state.errors
        };
        
        wkit.SaveToRaw(state.outputJson, JSON.stringify(jsonData, null, 2));
        Logger.Info(`JSON results saved to: ${state.outputJson}`);
        
        // Save text report
        let textReport = `GENERIC NODE FINDER REPORT\n`;
        textReport += `Target Node Type: ${TARGET_NODE_TYPE}\n`;
        textReport += `Search Date: ${new Date().toISOString()}\n`;
        textReport += `Files Processed: ${state.processedFiles}\n`;
        textReport += `Total Nodes Found: ${state.totalNodesFound}\n`;
        textReport += `Results Shown: ${state.foundNodes.length}\n`;
        textReport += `Duration: ${duration} seconds\n\n`;
        
        textReport += `DETAILED RESULTS:\n`;
        textReport += `=`.repeat(40) + `\n`;
        
        for (let i = 0; i < state.foundNodes.length; i++) {
            const node = state.foundNodes[i];
            textReport += `\nResult ${i + 1}:\n`;
            textReport += `-`.repeat(20) + `\n`;
            textReport += `File: ${node.fileName}\n`;
            textReport += `Node ID: ${node.nodeId}\n`;
            textReport += `Node Type: ${node.nodeType}\n`;
            textReport += `File Type: ${node.fileType}\n`;
            
            if (SHOW_FULL_JSON && node.completeJson) {
                textReport += `Complete JSON:\n${node.completeJson}\n`;
            } else {
                textReport += `Key Properties:\n${JSON.stringify(node.keyProperties, null, 2)}\n`;
            }
        }
        
        if (state.errors.length > 0) {
            textReport += `\nERRORS:\n`;
            for (const error of state.errors.slice(0, 20)) {
                textReport += `${error}\n`;
            }
        }
        
        wkit.SaveToRaw(state.outputTxt, textReport);
        Logger.Info(`Text report saved to: ${state.outputTxt}`);
        
    } catch (error) {
        Logger.Error(`Could not save results: ${error.message}`);
    }
}

// ===== COMPLETION DIALOG =====
function showCompletionDialog(state, duration) {
    const message = `Generic Node Finder Complete!\n\n` +
                   `Target: ${TARGET_NODE_TYPE}\n` +
                   `Files processed: ${state.processedFiles}\n` +
                   `Files with target nodes: ${state.filesWithTargetNodes}\n` +
                   `Total nodes found: ${state.totalNodesFound}\n` +
                   `Results displayed: ${state.foundNodes.length}\n` +
                   `Duration: ${duration} seconds\n\n` +
                   `Check the log for complete node details.\n` +
                   (SAVE_RESULTS ? `\nResults saved to:\n${state.outputJson}\n${state.outputTxt}` : '');
    
    wkit.ShowMessageBox(message, 'Node Search Complete', 0, 0);
}

// ===== RUN THE SEARCH =====
main(); 
