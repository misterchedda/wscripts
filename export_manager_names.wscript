// Extract questEventManagerNodeDefinition data from quest and scene files
// @author MisterChedda
// @version 1.0
// Searches for questEventManagerNodeDefinition nodes and extracts key data to CSV format

import * as Logger from 'Logger.wscript';
import * as TypeHelper from 'TypeHelper.wscript';

// ===== CONFIGURATION =====
const INCLUDE_QUESTPHASE = true;        // Search in .questphase files
const INCLUDE_SCENE = true;             // Search in .scene files
const MAX_FILES_TO_PROCESS = 0;           // 0 = no limit, process all files
const SHOW_PROGRESS_EVERY = 100;         // Show progress every N files
const MAX_NODES_PER_FILE = 0;            // 0 = no limit, process all files regardless of node count

// ===== MAIN FUNCTION =====
function main() {
    Logger.Info("=== Quest Event Manager Node Extractor ===");
    Logger.Info(`Include .questphase: ${INCLUDE_QUESTPHASE}`);
    Logger.Info(`Include .scene: ${INCLUDE_SCENE}`);
    
    const state = initializeState();
    
    try {
        // Phase 1: Collect target files from archives
        Logger.Info("Phase 1: Collecting files from game archives...");
        collectTargetFiles(state);
        
        if (state.targetFiles.length === 0) {
            Logger.Warning("No .questphase or .scene files found in archives!");
            return;
        }
        
        Logger.Info(`Found ${state.targetFiles.length} target files`);
        
        // Phase 2: Extract quest event manager nodes
        Logger.Info("Phase 2: Extracting questEventManagerNodeDefinition data...");
        extractNodes(state);
        
        // Phase 3: Generate CSV output
        Logger.Info("Phase 3: Generating CSV output...");
        generateCSVOutput(state);
        
        Logger.Info("=== Extraction completed! ===");
        
    } catch (error) {
        Logger.Error("Fatal error during extraction: " + error.message);
        wkit.ShowMessageBox(
            "Extraction failed with error:\n" + error.message,
            "Extraction Error", 2, 0
        );
    }
}

// ===== STATE MANAGEMENT =====
function initializeState() {
    return {
        targetFiles: [],
        processedFiles: 0,
        skippedFiles: 0,
        extractedNodes: [],
        totalNodes: 0,
        errors: [],
        startTime: Date.now()
    };
}

// ===== FILE COLLECTION =====
function collectTargetFiles(state) {
    Logger.Info("Scanning game archives for target files...");
    
    let fileCount = 0;
    const archiveFiles = wkit.GetArchiveFiles();
    
    for (const gameFile of archiveFiles) {
        if (!gameFile || !gameFile.FileName) {
            continue;
        }
        
        const fileName = gameFile.FileName.toLowerCase();
        const shouldInclude = 
            (INCLUDE_QUESTPHASE && fileName.endsWith('.questphase')) ||
            (INCLUDE_SCENE && fileName.endsWith('.scene'));
            
        if (shouldInclude) {
            state.targetFiles.push(gameFile);
            fileCount++;
            
            // No file limit when MAX_FILES_TO_PROCESS is 0
            if (MAX_FILES_TO_PROCESS > 0 && fileCount >= MAX_FILES_TO_PROCESS) {
                Logger.Warning(`Reached maximum file limit (${MAX_FILES_TO_PROCESS}). Some files may be skipped.`);
                break;
            }
        }
    }
    
    Logger.Info(`Collected ${fileCount} target files for processing`);
}

// ===== NODE EXTRACTION =====
function extractNodes(state) {
    let processed = 0;
    
    for (const gameFile of state.targetFiles) {
        try {
            processed++;
            
            // Progress update
            if (processed % SHOW_PROGRESS_EVERY === 0) {
                Logger.Info(`Progress: ${processed}/${state.targetFiles.length} files processed (${state.extractedNodes.length} nodes found so far)`);
            }
            
            // Load file content as JSON
            const fileContent = wkit.GameFileToJson(gameFile);
            if (!fileContent) {
                Logger.Warning(`Could not load content for: ${gameFile.FileName}`);
                state.errors.push(`Failed to load: ${gameFile.FileName}`);
                continue;
            }
            
            // Parse JSON
            let parsedContent;
            try {
                parsedContent = TypeHelper.JsonParse(fileContent);
            } catch (parseError) {
                Logger.Warning(`Could not parse JSON for: ${gameFile.FileName}`);
                state.errors.push(`Failed to parse: ${gameFile.FileName} - ${parseError.message}`);
                continue;
            }
            
            if (!parsedContent) {
                continue;
            }
            
            // Check node count and skip if file is too large (only if limit is set)
            const nodeCount = getNodeCount(parsedContent, gameFile.FileName);
            if (MAX_NODES_PER_FILE > 0 && nodeCount > MAX_NODES_PER_FILE) {
                Logger.Info(`Skipping ${gameFile.FileName}: ${nodeCount} nodes (exceeds limit of ${MAX_NODES_PER_FILE})`);
                state.skippedFiles++;
                continue;
            }
            
            if (nodeCount > 0) {
                Logger.Debug(`Processing ${gameFile.FileName}: ${nodeCount} nodes`);
            }
            
            // Search for questEventManagerNodeDefinition nodes
            const fileResults = [];
            searchForQuestEventManagers(parsedContent, fileResults, gameFile.FileName);
            
            if (fileResults.length > 0) {
                Logger.Info(`FOUND: ${gameFile.FileName}: ${fileResults.length} questEventManagerNodeDefinition(s)`);
                state.extractedNodes.push(...fileResults);
                state.totalNodes += fileResults.length;
            }
            
        } catch (error) {
            Logger.Error(`Error processing ${gameFile.FileName}: ${error.message}`);
            state.errors.push(`Error processing ${gameFile.FileName}: ${error.message}`);
        }
    }
    
    state.processedFiles = processed;
}

// ===== NODE COUNTING FUNCTION =====
function getNodeCount(parsedContent, fileName) {
    try {
        const lowerFileName = fileName.toLowerCase();
        
        if (lowerFileName.endsWith('.scene')) {
            // Scene files: graph is in sceneGraph.Data.graph
            if (parsedContent.Data && 
                parsedContent.Data.RootChunk && 
                parsedContent.Data.RootChunk.sceneGraph &&
                parsedContent.Data.RootChunk.sceneGraph.Data &&
                parsedContent.Data.RootChunk.sceneGraph.Data.graph &&
                Array.isArray(parsedContent.Data.RootChunk.sceneGraph.Data.graph)) {
                return parsedContent.Data.RootChunk.sceneGraph.Data.graph.length;
            }
            
        } else if (lowerFileName.endsWith('.questphase')) {
            // Quest phase files: check graph.nodes
            if (parsedContent.Data && 
                parsedContent.Data.RootChunk && 
                parsedContent.Data.RootChunk.graph &&
                parsedContent.Data.RootChunk.graph.nodes &&
                Array.isArray(parsedContent.Data.RootChunk.graph.nodes)) {
                return parsedContent.Data.RootChunk.graph.nodes.length;
            }
        }
        
        return 0;
        
    } catch (error) {
        Logger.Warning(`Error counting nodes in ${fileName}: ${error.message}`);
        return 0;
    }
}

// ===== RECURSIVE SEARCH FOR QUEST EVENT MANAGERS =====
function searchForQuestEventManagers(obj, results, fileName, currentPath = "") {
    if (typeof obj === 'object' && obj !== null) {
        // Check if this object is a questEventManagerNodeDefinition
        if (obj.$type === "questEventManagerNodeDefinition") {
            Logger.Debug(`Found questEventManagerNodeDefinition at: ${currentPath}`);
            
            // Extract the required fields
            const extractedData = extractNodeData(obj, fileName, currentPath);
            if (extractedData) {
                results.push(extractedData);
            }
        }
        
        // Recursively search all properties
        if (Array.isArray(obj)) {
            for (let i = 0; i < obj.length; i++) {
                const newPath = currentPath ? `${currentPath}[${i}]` : `[${i}]`;
                searchForQuestEventManagers(obj[i], results, fileName, newPath);
            }
        } else {
            for (const key in obj) {
                if (obj.hasOwnProperty(key)) {
                    const newPath = currentPath ? `${currentPath}.${key}` : key;
                    searchForQuestEventManagers(obj[key], results, fileName, newPath);
                }
            }
        }
    }
}

// ===== DATA EXTRACTION FROM NODE =====
function extractNodeData(node, fileName, path) {
    try {
        // Extract required fields with safe access
        const eventType = getNestedValue(node, 'event.Data.$type') || '';
        const managerName = getNestedValue(node, 'managerName') || '';
        const isObjectPlayer = getNestedValue(node, 'isObjectPlayer');
        const isUiEvent = getNestedValue(node, 'isUiEvent');
        const psClassName = getNestedValue(node, 'PSClassName.$value') || '';
        const nodeId = getNestedValue(node, 'id') || '';
        
        return {
            fileName: fileName,
            path: path,
            nodeId: nodeId,
            eventType: eventType,
            managerName: managerName,
            isObjectPlayer: isObjectPlayer !== undefined ? isObjectPlayer : '',
            isUiEvent: isUiEvent !== undefined ? isUiEvent : '',
            psClassName: psClassName
        };
        
    } catch (error) {
        Logger.Warning(`Error extracting data from node at ${path}: ${error.message}`);
        return null;
    }
}

// ===== UTILITY FUNCTION FOR SAFE NESTED ACCESS =====
function getNestedValue(obj, path) {
    const keys = path.split('.');
    let current = obj;
    
    for (const key of keys) {
        if (current === null || current === undefined || typeof current !== 'object') {
            return undefined;
        }
        current = current[key];
    }
    
    return current;
}

// ===== CSV OUTPUT GENERATION =====
function generateCSVOutput(state) {
    const endTime = Date.now();
    const duration = Math.round((endTime - state.startTime) / 1000);
    
    Logger.Info("=== Extraction Results ===");
    Logger.Info(`Files processed: ${state.processedFiles}`);
    Logger.Info(`Files skipped (too many nodes): ${state.skippedFiles}`);
    Logger.Info(`Total questEventManagerNodeDefinition nodes found: ${state.totalNodes}`);
    Logger.Info(`Errors encountered: ${state.errors.length}`);
    Logger.Info(`Duration: ${duration} seconds`);
    
    if (state.extractedNodes.length === 0) {
        Logger.Warning("No questEventManagerNodeDefinition nodes found!");
        wkit.ShowMessageBox("No questEventManagerNodeDefinition nodes found!", "Extraction Complete", 1, 0);
        return;
    }
    
    // Generate CSV content
    let csvContent = generateCSVContent(state, duration);
    
    // Save CSV to raw folder
    const csvFileName = `questEventManagerNodes_${Date.now()}.txt`;
    try {
        wkit.SaveToRaw(csvFileName, csvContent);
        Logger.Info(`CSV data saved to: ${csvFileName}`);
    } catch (error) {
        Logger.Error(`Could not save CSV: ${error.message}`);
    }
    
    // Show completion message
    const message = `Quest Event Manager Extraction Complete!\n\n` +
                   `Files processed: ${state.processedFiles}\n` +
                   `Files skipped (too many nodes): ${state.skippedFiles}\n` +
                   `Nodes found: ${state.totalNodes}\n` +
                   `Duration: ${duration}s\n\n` +
                   `CSV data saved to raw folder:\n${csvFileName}`;
    
    wkit.ShowMessageBox(message, "Extraction Complete", 0, 0);
}

function generateCSVContent(state, duration) {
    let csv = "Quest Event Manager Node Extraction Results\n";
    csv += "=".repeat(60) + "\n\n";
    csv += `Generated: ${new Date().toISOString()}\n`;
    csv += `Files Processed: ${state.processedFiles}\n`;
    csv += `Files Skipped: ${state.skippedFiles}\n`;
    csv += `Nodes Found: ${state.totalNodes}\n`;
    csv += `Duration: ${duration} seconds\n\n`;
    
    // CSV Header
    csv += "FileName,Path,NodeId,EventType,ManagerName,IsObjectPlayer,IsUiEvent,PSClassName\n";
    
    // CSV Data rows
    for (const node of state.extractedNodes) {
        // Escape any commas or quotes in the data
        const escapedData = [
            escapeCSVField(node.fileName),
            escapeCSVField(node.path),
            escapeCSVField(String(node.nodeId)),
            escapeCSVField(node.eventType),
            escapeCSVField(node.managerName),
            escapeCSVField(String(node.isObjectPlayer)),
            escapeCSVField(String(node.isUiEvent)),
            escapeCSVField(node.psClassName)
        ];
        
        csv += escapedData.join(',') + '\n';
    }
    
    if (state.errors.length > 0) {
        csv += "\n\nERRORS ENCOUNTERED:\n";
        csv += "-".repeat(30) + "\n";
        for (const error of state.errors) {
            csv += `${error}\n`;
        }
    }
    
    return csv;
}

// ===== CSV FIELD ESCAPING =====
function escapeCSVField(field) {
    if (field === null || field === undefined) {
        return '';
    }
    
    const stringField = String(field);
    
    // If field contains comma, newline, or quote, wrap in quotes and escape internal quotes
    if (stringField.includes(',') || stringField.includes('\n') || stringField.includes('"')) {
        return '"' + stringField.replace(/"/g, '""') + '"';
    }
    
    return stringField;
}

// Start the extraction
main(); 
