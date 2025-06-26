// DEEP ANALYSIS: Start/End Node Socket Investigation
// @author MisterChedda
// @version 2.0 - Comprehensive Start/End Node Investigation
// Searches ALL scene files for Start/End node connection patterns
// Provides exact file paths and node IDs for manual verification

import * as Logger from 'Logger.wscript';
import * as TypeHelper from 'TypeHelper.wscript';

// ===== CONFIGURATION =====
const SEARCH_PATTERNS = [
    {
        name: "CutDestination_Pattern",
        pattern: '"isockStamp":\\s*{[^}]*"name":\\s*1[^}]*"ordinal":\\s*0[^}]*}[\\s\\S]*?"nodeId":\\s*{[^}]*"id":\\s*(\\d+)',
        description: "Cut connections TO nodes (isockStamp with Name:1, Ordinal:0)"
    },
    {
        name: "Compatibility_Pattern", 
        pattern: '"isockStamp":\\s*{[^}]*"name":\\s*0[^}]*"ordinal":\\s*1[^}]*}[\\s\\S]*?"nodeId":\\s*{[^}]*"id":\\s*(\\d+)',
        description: "Compatibility connections TO nodes (isockStamp with Name:0, Ordinal:1)"
    },
    {
        name: "Normal_Pattern",
        pattern: '"isockStamp":\\s*{[^}]*"name":\\s*0[^}]*"ordinal":\\s*0[^}]*}[\\s\\S]*?"nodeId":\\s*{[^}]*"id":\\s*(\\d+)', 
        description: "Normal connections TO nodes (isockStamp with Name:0, Ordinal:0)"
    }
];

const CONTEXT_LENGTH = 1200;             // More context for analysis
const INCLUDE_QUESTPHASE = false;       // Focus on scene files only  
const INCLUDE_SCENE = true;             // Search in .scene files
const IGNOREIDANDLOCSTORE = true;       // Skip debugSymbols and locStore sections
const MAX_FILES_TO_PROCESS = 99999;    // Search ALL files
const SHOW_PROGRESS_EVERY = 200;        // Show progress every N files
const SAVE_PROGRESS_EVERY = 100;        // Save progress report every N files
const MAX_NODES_PER_FILE = 1000;       // Higher limit for comprehensive search

// Focus on Start/End nodes specifically
const FOCUS_NODE_TYPES = ["scnEndNode", "scnStartNode"];
const ALL_SCENE_NODE_TYPES = [
    "scnChoiceNode", "scnSectionNode", "scnRewindableSectionNode", 
    "scnHubNode", "scnAndNode", "scnXorNode", "scnRandomizerNode",
    "scnInterruptManagerNode", "scnEndNode", "scnStartNode"
];

// ===== MAIN FUNCTION =====
function main() {
    Logger.Info("=== DEEP ANALYSIS: Start/End Node Socket Investigation ===");
    Logger.Info("Searching ALL scene files for Start/End node connection patterns...");
    Logger.Info("Focus: Exact file paths + node IDs for manual verification");
    
    const state = initializeState();
    
    try {
        // Phase 1: Collect ALL scene files from archives
        Logger.Info("Phase 1: Collecting ALL scene files from game archives...");
        collectAllTargetFiles(state);
        
        if (state.targetFiles.length === 0) {
            Logger.Warning("No scene files found in archives!");
            return;
        }
        
        Logger.Info(`Found ${state.targetFiles.length} scene files to analyze`);
        
        // Phase 2: Deep search through files
        Logger.Info("Phase 2: Deep searching for socket connection patterns...");
        searchFiles(state);
        
        // Phase 3: Generate comprehensive results
        Logger.Info("Phase 3: Generating comprehensive analysis...");
        generateComprehensiveResults(state);
        
        Logger.Info("=== Deep analysis completed! ===");
        
    } catch (error) {
        Logger.Error("Fatal error during deep analysis: " + error.message);
        wkit.ShowMessageBox(
            "Deep analysis failed with error:\n" + error.message,
            "Analysis Error", 2, 0
        );
    }
}

// ===== STATE MANAGEMENT =====
function initializeState() {
    return {
        targetFiles: [],
        processedFiles: 0,
        skippedFiles: 0,
        patternResults: {},
        totalMatches: 0,
        errors: [],
        startTime: Date.now(),
        
        // Detailed Start/End node tracking
        startNodeDetails: {
            withCut: [],
            withNormal: [],
            withCompatibility: [],
            totalStartNodes: 0
        },
        endNodeDetails: {
            withCut: [],
            withNormal: [], 
            withCompatibility: [],
            totalEndNodes: 0
        },
        
        // All connections for verification
        allConnections: [],
        suspiciousConnections: [],
        
        // Progressive saving
        reportFileName: `progressive_start_end_analysis_${Date.now()}.txt`,
        lastSaveTime: Date.now()
    };
}

// ===== FILE COLLECTION =====
function collectAllTargetFiles(state) {
    Logger.Info("Scanning game archives for ALL scene files...");
    
    let fileCount = 0;
    let skippedVersions = 0;
    const archiveFiles = wkit.GetArchiveFiles();
    
    for (const gameFile of archiveFiles) {
        if (!gameFile || !gameFile.FileName) {
            continue;
        }
        
        const fileName = gameFile.FileName.toLowerCase();
        
        // Skip version folders (duplicates)
        if (fileName.includes("versions")) {
            skippedVersions++;
            continue;
        }
        
        const shouldInclude = 
            (INCLUDE_QUESTPHASE && fileName.endsWith('.questphase')) ||
            (INCLUDE_SCENE && fileName.endsWith('.scene'));
            
        if (shouldInclude) {
            state.targetFiles.push(gameFile);
            fileCount++;
        }
    }
    
    // Initialize pattern results
    for (const pattern of SEARCH_PATTERNS) {
        state.patternResults[pattern.name] = {
            pattern: pattern,
            matchingFiles: [],
            totalMatches: 0
        };
    }
    
    Logger.Info(`Collected ${fileCount} scene files for processing`);
    Logger.Info(`Skipped ${skippedVersions} files in version folders`);
}

// ===== PROGRESSIVE SAVING =====
function saveProgressReport(state, isIntermediate = true) {
    try {
        const currentTime = Date.now();
        const duration = Math.round((currentTime - state.startTime) / 1000);
        
        let report = `${isIntermediate ? 'PROGRESSIVE' : 'FINAL'} Start/End Node Analysis Report\n`;
        report += "=".repeat(60) + "\n\n";
        report += `Generated: ${new Date().toISOString()}\n`;
        report += `Status: ${isIntermediate ? 'IN PROGRESS' : 'COMPLETE'}\n`;
        report += `Files Processed: ${state.processedFiles}/${state.targetFiles.length}\n`;
        report += `Duration so far: ${duration} seconds\n\n`;
        
        // Current findings
        report += "CURRENT FINDINGS:\n";
        report += "-".repeat(30) + "\n";
        report += `Total Start nodes found: ${state.startNodeDetails.totalStartNodes}\n`;
        report += `Total End nodes found: ${state.endNodeDetails.totalEndNodes}\n`;
        report += `Start nodes with Cut connections: ${state.startNodeDetails.withCut.length}\n`;
        report += `Start nodes with Normal connections: ${state.startNodeDetails.withNormal.length}\n`;
        report += `Start nodes with Compatibility connections: ${state.startNodeDetails.withCompatibility.length}\n`;
        report += `End nodes with Cut connections: ${state.endNodeDetails.withCut.length}\n`;
        report += `End nodes with Normal connections: ${state.endNodeDetails.withNormal.length}\n`;
        report += `End nodes with Compatibility connections: ${state.endNodeDetails.withCompatibility.length}\n\n`;
        
        // Critical findings so far
                 if (state.startNodeDetails.withCut.length > 0) {
             report += "START NODES WITH CUT CONNECTIONS FOUND SO FAR:\n";
             report += "-".repeat(50) + "\n";
             for (const connection of state.startNodeDetails.withCut) {
                 report += `  ${connection.filePath} - Node ${connection.targetNodeId}\n`;
                 report += `    Name: ${connection.socketName}, Ordinal: ${connection.socketOrdinal}\n`;
                 report += `    Pattern snippet: ${connection.socketPattern.substring(0, 100)}...\n`;
             }
             report += "\n";
         }
        
        if (state.endNodeDetails.withCompatibility.length > 0) {
            report += "END NODES WITH COMPATIBILITY CONNECTIONS (PROBLEMATIC):\n";
            report += "-".repeat(55) + "\n";
            for (let i = 0; i < Math.min(50, state.endNodeDetails.withCompatibility.length); i++) {
                const connection = state.endNodeDetails.withCompatibility[i];
                report += `  ${connection.filePath} - Node ${connection.targetNodeId}\n`;
            }
            if (state.endNodeDetails.withCompatibility.length > 50) {
                report += `  ... and ${state.endNodeDetails.withCompatibility.length - 50} more\n`;
            }
            report += "\n";
        }
        
        // Errors encountered
        if (state.errors.length > 0) {
            report += "ERRORS ENCOUNTERED:\n";
            report += "-".repeat(30) + "\n";
            for (const error of state.errors.slice(0, 20)) {
                report += `${error}\n`;
            }
            if (state.errors.length > 20) {
                report += `... and ${state.errors.length - 20} more errors\n`;
            }
        }
        
        wkit.SaveToRaw(state.reportFileName, report);
        state.lastSaveTime = currentTime;
        
        if (isIntermediate) {
            Logger.Info(`Progress saved to: ${state.reportFileName}`);
        }
        
    } catch (error) {
        Logger.Warning(`Could not save progress report: ${error.message}`);
    }
}

// ===== FILE SEARCHING =====
function searchFiles(state) {
    let processed = 0;
    
    for (const gameFile of state.targetFiles) {
        try {
            processed++;
            
            // Progress update
            if (processed % SHOW_PROGRESS_EVERY === 0) {
                Logger.Info(`Progress: ${processed}/${state.targetFiles.length} files processed`);
            }
            
            // Progressive save
            if (processed % SAVE_PROGRESS_EVERY === 0) {
                saveProgressReport(state, true);
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
            
            // Check node count and skip if file is too large
            const nodeCount = getNodeCount(parsedContent, gameFile.FileName);
            if (nodeCount > MAX_NODES_PER_FILE) {
                state.skippedFiles++;
                continue;
            }
            
            // Get Start/End nodes in this file for detailed tracking
            const startEndNodes = extractStartEndNodes(parsedContent);
            state.startNodeDetails.totalStartNodes += startEndNodes.startNodes.length;
            state.endNodeDetails.totalEndNodes += startEndNodes.endNodes.length;
            
            // Search for each pattern
            for (const searchPattern of SEARCH_PATTERNS) {
                const searchResults = { count: 0, contexts: [] };
                
                // Search in raw JSON string with regex
                searchWithRegexInJsonString(fileContent, searchPattern.pattern, searchResults, gameFile.FileName);
                
                if (searchResults.count > 0) {
                    // Analyze connections with detailed Start/End node focus
                    const connectionAnalysis = analyzeConnectionsWithDetail(
                        searchResults.contexts, 
                        parsedContent, 
                        gameFile.FileName,
                        searchPattern.name
                    );
                    
                    // Track Start/End node connections specifically
                    trackStartEndConnections(connectionAnalysis, state, searchPattern.name);
                    
                    // Store all connections for comprehensive analysis
                    state.allConnections.push(...connectionAnalysis);
                    
                    // Update pattern results
                    state.patternResults[searchPattern.name].matchingFiles.push({
                        fileName: gameFile.FileName,
                        matchCount: searchResults.count,
                        startEndConnections: connectionAnalysis.filter(c => c.isStartNode || c.isEndNode)
                    });
                    
                    state.patternResults[searchPattern.name].totalMatches += searchResults.count;
                    state.totalMatches += searchResults.count;
                }
            }
            
        } catch (error) {
            Logger.Error(`Error processing ${gameFile.FileName}: ${error.message}`);
            state.errors.push(`Error processing ${gameFile.FileName}: ${error.message}`);
        }
    }
    
    state.processedFiles = processed;
    
    // Final save after processing all files
    saveProgressReport(state, true);
}

// ===== DETAILED CONNECTION ANALYSIS =====
function analyzeConnectionsWithDetail(contexts, parsedContent, fileName, patternName) {
    const connections = [];
    
    try {
        // Get all scene nodes from the file
        const allNodes = extractAllSceneNodes(parsedContent);
        
        for (const context of contexts) {
            // The regex now captures the nodeId directly in the pattern
            // Extract nodeId from the regex match groups
            const regexMatch = new RegExp(SEARCH_PATTERNS.find(p => p.name === patternName).pattern, 'g').exec(context.fullMatch);
            
            if (regexMatch && regexMatch[1]) {
                const targetNodeId = parseInt(regexMatch[1]);
                
                // Check if this nodeId corresponds to a scene node
                const targetNode = allNodes.find(node => node.id === targetNodeId);
                if (targetNode) {
                    // Extract the specific name/ordinal values from the isockStamp
                    const nameMatch = context.fullMatch.match(/"name":\s*(\d+)/);
                    const ordinalMatch = context.fullMatch.match(/"ordinal":\s*(\d+)/);
                    
                    const connection = {
                        fileName: fileName,
                        filePath: fileName, // Full path for manual verification
                        targetNodeId: targetNodeId,
                        targetNodeType: targetNode.type,
                        socketPattern: context.fullMatch,
                        patternName: patternName,
                        isStartNode: targetNode.type === "scnStartNode",
                        isEndNode: targetNode.type === "scnEndNode",
                        context: context.value,
                        socketName: nameMatch ? parseInt(nameMatch[1]) : -1,
                        socketOrdinal: ordinalMatch ? parseInt(ordinalMatch[1]) : -1
                    };
                    
                    connections.push(connection);
                    
                    // Flag suspicious connections
                    if ((connection.isStartNode || connection.isEndNode) && 
                        (patternName === "CutDestination_Pattern" || patternName === "Compatibility_Pattern")) {
                        connection.suspicious = true;
                        Logger.Info(`FOUND: ${connection.isStartNode ? 'Start' : 'End'} node ${connection.targetNodeId} in ${fileName} with ${patternName} (Name:${connection.socketName}, Ord:${connection.socketOrdinal})`);
                    }
                }
            }
        }
    } catch (error) {
        Logger.Warning(`Error analyzing connections in ${fileName}: ${error.message}`);
    }
    
    return connections;
}

// ===== TRACK START/END NODE CONNECTIONS =====
function trackStartEndConnections(connections, state, patternName) {
    for (const connection of connections) {
        if (connection.isStartNode) {
            if (patternName === "CutDestination_Pattern") {
                state.startNodeDetails.withCut.push(connection);
            } else if (patternName === "Normal_Pattern") {
                state.startNodeDetails.withNormal.push(connection);
            } else if (patternName === "Compatibility_Pattern") {
                state.startNodeDetails.withCompatibility.push(connection);
            }
        }
        
        if (connection.isEndNode) {
            if (patternName === "CutDestination_Pattern") {
                state.endNodeDetails.withCut.push(connection);
            } else if (patternName === "Normal_Pattern") {
                state.endNodeDetails.withNormal.push(connection);
            } else if (patternName === "Compatibility_Pattern") {
                state.endNodeDetails.withCompatibility.push(connection);
            }
        }
        
        // Track suspicious connections
        if (connection.suspicious) {
            state.suspiciousConnections.push(connection);
        }
    }
}

// ===== EXTRACT START/END NODES =====
function extractStartEndNodes(parsedContent) {
    const startNodes = [];
    const endNodes = [];
    
    try {
        if (parsedContent.Data && 
            parsedContent.Data.RootChunk && 
            parsedContent.Data.RootChunk.sceneGraph &&
            parsedContent.Data.RootChunk.sceneGraph.Data &&
            parsedContent.Data.RootChunk.sceneGraph.Data.graph &&
            Array.isArray(parsedContent.Data.RootChunk.sceneGraph.Data.graph)) {
            
            const graph = parsedContent.Data.RootChunk.sceneGraph.Data.graph;
            
            for (const nodeHandle of graph) {
                if (nodeHandle && nodeHandle.Data && nodeHandle.Data.nodeId) {
                    const nodeData = nodeHandle.Data;
                    const nodeType = nodeData.$type;
                    const nodeId = nodeData.nodeId.id;
                    
                    if (nodeType === "scnStartNode") {
                        startNodes.push({ id: nodeId, type: nodeType });
                    } else if (nodeType === "scnEndNode") {
                        endNodes.push({ id: nodeId, type: nodeType });
                    }
                }
            }
        }
    } catch (error) {
        Logger.Warning(`Error extracting Start/End nodes: ${error.message}`);
    }
    
    return { startNodes, endNodes };
}

// ===== EXTRACT ALL SCENE NODES =====
function extractAllSceneNodes(parsedContent) {
    const allNodes = [];
    
    try {
        if (parsedContent.Data && 
            parsedContent.Data.RootChunk && 
            parsedContent.Data.RootChunk.sceneGraph &&
            parsedContent.Data.RootChunk.sceneGraph.Data &&
            parsedContent.Data.RootChunk.sceneGraph.Data.graph &&
            Array.isArray(parsedContent.Data.RootChunk.sceneGraph.Data.graph)) {
            
            const graph = parsedContent.Data.RootChunk.sceneGraph.Data.graph;
            
            for (const nodeHandle of graph) {
                if (nodeHandle && nodeHandle.Data && nodeHandle.Data.nodeId) {
                    const nodeData = nodeHandle.Data;
                    const nodeType = nodeData.$type;
                    const nodeId = nodeData.nodeId.id;
                    
                    if (ALL_SCENE_NODE_TYPES.includes(nodeType)) {
                        allNodes.push({
                            id: nodeId,
                            type: nodeType
                        });
                    }
                }
            }
        }
    } catch (error) {
        Logger.Warning(`Error extracting scene nodes: ${error.message}`);
    }
    
    return allNodes;
}

// ===== REGEX SEARCH FUNCTION =====
function searchWithRegexInJsonString(jsonString, regexPattern, results, fileName) {
    try {
        const regex = new RegExp(regexPattern, 'gi');
        let match;
        
        while ((match = regex.exec(jsonString)) !== null) {
            const matchIndex = match.index;
            
            // Extract context around the match
            const halfContext = Math.floor(CONTEXT_LENGTH / 2);
            const preContextStart = Math.max(0, matchIndex - halfContext);
            const postContextEnd = Math.min(matchIndex + match[0].length + halfContext, jsonString.length);
            
            const fullContext = jsonString.substring(preContextStart, postContextEnd);
            const startEllipsis = preContextStart > 0 ? '...' : '';
            const endEllipsis = postContextEnd < jsonString.length ? '...' : '';
            
            results.count++;
            results.contexts.push({
                path: "[isockStamp Pattern]",
                value: `${startEllipsis}${fullContext}${endEllipsis}`,
                fullMatch: match[0],
                matchPosition: matchIndex,
                contextLength: CONTEXT_LENGTH,
                rawContext: fullContext
            });
            
            // Prevent infinite loop on zero-length matches
            if (match[0].length === 0) {
                regex.lastIndex++;
            }
        }
    } catch (error) {
        Logger.Warning(`Regex search error in ${fileName}: ${error.message}`);
    }
}

// ===== NODE COUNTING FUNCTION =====
function getNodeCount(parsedContent, fileName) {
    try {
        if (parsedContent.Data && 
            parsedContent.Data.RootChunk && 
            parsedContent.Data.RootChunk.sceneGraph &&
            parsedContent.Data.RootChunk.sceneGraph.Data &&
            parsedContent.Data.RootChunk.sceneGraph.Data.graph &&
            Array.isArray(parsedContent.Data.RootChunk.sceneGraph.Data.graph)) {
            return parsedContent.Data.RootChunk.sceneGraph.Data.graph.length;
        }
        return 0;
    } catch (error) {
        Logger.Warning(`Error counting nodes in ${fileName}: ${error.message}`);
        return 0;
    }
}

// ===== COMPREHENSIVE RESULTS GENERATION =====
function generateComprehensiveResults(state) {
    const endTime = Date.now();
    const duration = Math.round((endTime - state.startTime) / 1000);
    
    Logger.Info("=== COMPREHENSIVE START/END NODE ANALYSIS ===");
    Logger.Info(`Files processed: ${state.processedFiles}`);
    Logger.Info(`Files skipped (too many nodes): ${state.skippedFiles}`);
    Logger.Info(`Total Start nodes found: ${state.startNodeDetails.totalStartNodes}`);
    Logger.Info(`Total End nodes found: ${state.endNodeDetails.totalEndNodes}`);
    Logger.Info(`Duration: ${duration} seconds`);
    
    // Detailed Start Node Analysis
    Logger.Info("\n=== START NODE DETAILED ANALYSIS ===");
    Logger.Info(`Start nodes with Cut connections (Name:1, Ord:0): ${state.startNodeDetails.withCut.length}`);
    Logger.Info(`Start nodes with Normal connections (Name:0, Ord:0): ${state.startNodeDetails.withNormal.length}`);
    Logger.Info(`Start nodes with Compatibility connections (Name:0, Ord:1): ${state.startNodeDetails.withCompatibility.length}`);
    
    // Print exact Start node details for manual verification
    if (state.startNodeDetails.withCut.length > 0) {
        Logger.Info("\nSTART NODES WITH CUT CONNECTIONS:");
        for (const connection of state.startNodeDetails.withCut) {
            Logger.Info(`  File: ${connection.filePath}`);
            Logger.Info(`  Node ID: ${connection.targetNodeId}`);
            Logger.Info(`  Pattern: ${connection.socketPattern}`);
        }
    }
    
    if (state.startNodeDetails.withNormal.length > 0) {
        Logger.Info("\nSTART NODES WITH NORMAL CONNECTIONS (first 10):");
        for (let i = 0; i < Math.min(10, state.startNodeDetails.withNormal.length); i++) {
            const connection = state.startNodeDetails.withNormal[i];
            Logger.Info(`  File: ${connection.filePath}`);
            Logger.Info(`  Node ID: ${connection.targetNodeId}`);
        }
    }
    
    if (state.startNodeDetails.withCompatibility.length > 0) {
        Logger.Info("\nSTART NODES WITH COMPATIBILITY CONNECTIONS:");
        for (const connection of state.startNodeDetails.withCompatibility) {
            Logger.Info(`  File: ${connection.filePath}`);
            Logger.Info(`  Node ID: ${connection.targetNodeId}`);
        }
    }
    
    // Detailed End Node Analysis  
    Logger.Info("\n=== END NODE DETAILED ANALYSIS ===");
    Logger.Info(`End nodes with Cut connections (Name:1, Ord:0): ${state.endNodeDetails.withCut.length}`);
    Logger.Info(`End nodes with Normal connections (Name:0, Ord:0): ${state.endNodeDetails.withNormal.length}`);
    Logger.Info(`End nodes with Compatibility connections (Name:0, Ord:1): ${state.endNodeDetails.withCompatibility.length}`);
    
    // Print exact End node details for manual verification
    if (state.endNodeDetails.withCut.length > 0) {
        Logger.Info("\nEND NODES WITH CUT CONNECTIONS:");
        for (const connection of state.endNodeDetails.withCut) {
            Logger.Info(`  File: ${connection.filePath}`);
            Logger.Info(`  Node ID: ${connection.targetNodeId}`);
        }
    }
    
    if (state.endNodeDetails.withCompatibility.length > 0) {
        Logger.Info("\nEND NODES WITH COMPATIBILITY CONNECTIONS (these are PROBLEMATIC!):");
        for (let i = 0; i < Math.min(20, state.endNodeDetails.withCompatibility.length); i++) {
            const connection = state.endNodeDetails.withCompatibility[i];
            Logger.Info(`  File: ${connection.filePath}`);
            Logger.Info(`  Node ID: ${connection.targetNodeId}`);
            Logger.Info(`  Pattern: ${connection.socketPattern}`);
        }
    }
    
    // Save final comprehensive report (overwriting progressive saves)
    saveProgressReport(state, false);
    
    // Also generate detailed report with all findings
    const detailedReportContent = generateDetailedReport(state, duration);
    const detailedReportFileName = `detailed_${state.reportFileName}`;
    
    try {
        wkit.SaveToRaw(detailedReportFileName, detailedReportContent);
        Logger.Info(`Final report saved to: ${state.reportFileName}`);
        Logger.Info(`Detailed report saved to: ${detailedReportFileName}`);
    } catch (error) {
        Logger.Error(`Could not save detailed report: ${error.message}`);
    }
    
    // Show completion message
    const startCutCount = state.startNodeDetails.withCut.length;
    const endCompatCount = state.endNodeDetails.withCompatibility.length;
    
    const message = `Comprehensive Start/End Node Analysis Complete!\n\n` +
                   `Files processed: ${state.processedFiles}\n` +
                   `Start nodes analyzed: ${state.startNodeDetails.totalStartNodes}\n` +
                   `End nodes analyzed: ${state.endNodeDetails.totalEndNodes}\n\n` +
                   `CRITICAL FINDINGS:\n` +
                   `Start nodes with Cut inputs: ${startCutCount}\n` +
                   `End nodes with Compatibility inputs: ${endCompatCount}\n\n` +
                   `The Compatibility connections to End nodes explain\n` +
                   `why WolvenKit crashes on certain scenes!\n\n` +
                                       `Check the log for exact file paths and node IDs\n` +
                    `Reports saved: ${state.reportFileName}\n` +
                    `Duration: ${duration}s`;
    
    wkit.ShowMessageBox(message, "Comprehensive Analysis Complete", 0, 0);
}

function generateDetailedReport(state, duration) {
    let report = "Comprehensive Start/End Node Socket Analysis\n";
    report += "=".repeat(60) + "\n\n";
    report += `Generated: ${new Date().toISOString()}\n`;
    report += `Files Processed: ${state.processedFiles}\n`;
    report += `Duration: ${duration} seconds\n\n`;
    
    // Start Node Summary
    report += "START NODE ANALYSIS:\n";
    report += "-".repeat(30) + "\n";
    report += `Total Start nodes found: ${state.startNodeDetails.totalStartNodes}\n`;
    report += `Start nodes with Cut connections: ${state.startNodeDetails.withCut.length}\n`;
    report += `Start nodes with Normal connections: ${state.startNodeDetails.withNormal.length}\n`;
    report += `Start nodes with Compatibility connections: ${state.startNodeDetails.withCompatibility.length}\n\n`;
    
    // End Node Summary
    report += "END NODE ANALYSIS:\n";
    report += "-".repeat(30) + "\n";
    report += `Total End nodes found: ${state.endNodeDetails.totalEndNodes}\n`;
    report += `End nodes with Cut connections: ${state.endNodeDetails.withCut.length}\n`;
    report += `End nodes with Normal connections: ${state.endNodeDetails.withNormal.length}\n`;
    report += `End nodes with Compatibility connections: ${state.endNodeDetails.withCompatibility.length}\n\n`;
    
    // Detailed connection listings
    report += "DETAILED CONNECTION LISTINGS:\n";
    report += "-".repeat(40) + "\n";
    
    // Start node Cut connections
    if (state.startNodeDetails.withCut.length > 0) {
        report += "Start Nodes with Cut Connections:\n";
        for (const connection of state.startNodeDetails.withCut) {
            report += `  ${connection.filePath} - Node ${connection.targetNodeId}\n`;
        }
        report += "\n";
    }
    
    // End node Compatibility connections (the problematic ones)
    if (state.endNodeDetails.withCompatibility.length > 0) {
        report += "End Nodes with Compatibility Connections (PROBLEMATIC):\n";
        for (const connection of state.endNodeDetails.withCompatibility) {
            report += `  ${connection.filePath} - Node ${connection.targetNodeId}\n`;
        }
        report += "\n";
    }
    
    return report;
}

// Start the comprehensive analysis
main(); 
