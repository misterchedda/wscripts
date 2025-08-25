// Search for string in quest phases and scene files directly from archives
// @author MisterChedda
// @version 1.1
// Searches all .questphase and .scene files in game archives for a given string
// and extracts context around each match
// No need to add files to project first!

import * as Logger from 'Logger.wscript';
import * as TypeHelper from 'TypeHelper.wscript';

// ===== CONFIGURATION ===== 
const SEARCH_STRING = "workspotnode"; // Change this to search for different strings
const INCLUDE_QUESTPHASE = true;       // Search in .questphase files
const INCLUDE_SCENE = false;            // Search in .scene files
const MAX_NODES_PER_FILE = 500;        // Skip files with more than N nodes
const MAX_FILES_TO_PROCESS = 99999;     // Limit results

const CONTEXT_LENGTH = 300;              // Total context characters (split evenly before/after the match)
const IGNOREIDANDLOCSTORE = true;       // Skip debugSymbols and locStore sections in .scene files for performance
const SHOW_PROGRESS_EVERY = 500;        // Show progress every N files

// ===== MAIN FUNCTION =====
function main() {
    Logger.Info("=== Archive File String Search ===");
    Logger.Info(`Searching for: "${SEARCH_STRING}"`);
    Logger.Info(`Context length: ${CONTEXT_LENGTH} characters (bidirectional)`);
    Logger.Info(`Include .questphase: ${INCLUDE_QUESTPHASE}`);
    Logger.Info(`Include .scene: ${INCLUDE_SCENE}`);
    Logger.Info(`Skip debugSymbols/locStore: ${IGNOREIDANDLOCSTORE}`);
    
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
        
        // Phase 2: Search through files
        Logger.Info("Phase 2: Searching files for string...");
        searchFiles(state);
        
        // Phase 3: Generate results
        Logger.Info("Phase 3: Generating results...");
        generateResults(state);
        
        Logger.Info("=== Search completed! ===");
        
    } catch (error) {
        Logger.Error("Fatal error during search: " + error.message);
        wkit.ShowMessageBox(
            "Search failed with error:\n" + error.message,
            "Search Error", 2, 0
        );
    }
}

// ===== STATE MANAGEMENT =====
function initializeState() {
    return {
        targetFiles: [],
        processedFiles: 0,
        skippedFiles: 0,
        matchingFiles: [],
        totalMatches: 0,
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
            
            if (fileCount >= MAX_FILES_TO_PROCESS) {
                Logger.Warning(`Reached maximum file limit (${MAX_FILES_TO_PROCESS}). Some files may be skipped.`);
                break;
            }
        }
    }
    
    Logger.Info(`Collected ${fileCount} target files for processing`);
}

// ===== FILE SEARCHING =====
function searchFiles(state) {
    let processed = 0;
    
    for (const gameFile of state.targetFiles) {
        try {
            processed++;
            
            // Progress update
            if (processed % SHOW_PROGRESS_EVERY === 0) {
                Logger.Info(`Progress: ${processed}/${state.targetFiles.length} files processed (${state.matchingFiles.length} matches so far)`);
            }
            
            // Load file content as JSON using the GameFile object directly
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
                // Logger.Info(`Skipping ${gameFile.FileName}: ${nodeCount} nodes (exceeds limit of ${MAX_NODES_PER_FILE})`);
                state.skippedFiles++;
                continue;
            }
            
            if (nodeCount > 0) {
                // Logger.Debug(`Processing ${gameFile.FileName}: ${nodeCount} nodes`);
            }
            
            // Search for string in the parsed content with context extraction
            const searchResults = { count: 0, contexts: [] };
            
            // Also search in the raw JSON string for better context extraction
            searchInJsonString(fileContent, SEARCH_STRING, searchResults, gameFile.FileName);
            
            // Also search in the parsed object structure
            searchInObject(parsedContent, SEARCH_STRING, searchResults, gameFile.FileName, "", gameFile.FileName.toLowerCase());
            
            if (searchResults.count > 0) {
                state.matchingFiles.push({
                    fileName: gameFile.FileName,
                    matchCount: searchResults.count,
                    contexts: searchResults.contexts.slice(0, 10) // Limit contexts to first 10
                });
                
                state.totalMatches += searchResults.count;
                Logger.Info(`MATCH: ${gameFile.FileName}: ${searchResults.count} instance(s)`);
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
        // Determine file type and get appropriate node count
        const lowerFileName = fileName.toLowerCase();
        
        // Debug logging to see the structure
        /*
        if (parsedContent.Data && parsedContent.Data.RootChunk) {
            Logger.Debug(`Checking node count for: ${fileName}`);
            if (lowerFileName.endsWith('.scene')) {
                Logger.Debug(`Scene file structure check - has sceneGraph: ${!!parsedContent.Data.RootChunk.sceneGraph}`);
                if (parsedContent.Data.RootChunk.sceneGraph) {
                    Logger.Debug(`sceneGraph has Data: ${!!parsedContent.Data.RootChunk.sceneGraph.Data}`);
                    if (parsedContent.Data.RootChunk.sceneGraph.Data) {
                        Logger.Debug(`sceneGraph.Data has graph: ${!!parsedContent.Data.RootChunk.sceneGraph.Data.graph}`);
                        if (parsedContent.Data.RootChunk.sceneGraph.Data.graph) {
                            Logger.Debug(`graph is array: ${Array.isArray(parsedContent.Data.RootChunk.sceneGraph.Data.graph)}`);
                            Logger.Debug(`graph length: ${Array.isArray(parsedContent.Data.RootChunk.sceneGraph.Data.graph) ? parsedContent.Data.RootChunk.sceneGraph.Data.graph.length : 'N/A'}`);
                        }
                    }
                }
            }
        } */
        
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
            
            // Fallback: check if graph is directly under RootChunk
            if (parsedContent.Data &&
                parsedContent.Data.RootChunk &&
                parsedContent.Data.RootChunk.graph &&
                Array.isArray(parsedContent.Data.RootChunk.graph)) {
                return parsedContent.Data.RootChunk.graph.length;
            }
            
        } else if (lowerFileName.endsWith('.questphase')) {
            // Quest phase files: check graph.nodes (nodes array inside graph object)
            if (parsedContent.Data && 
                parsedContent.Data.RootChunk && 
                parsedContent.Data.RootChunk.graph &&
                parsedContent.Data.RootChunk.graph.nodes &&
                Array.isArray(parsedContent.Data.RootChunk.graph.nodes)) {
                return parsedContent.Data.RootChunk.graph.nodes.length;
            }
            
            // Alternative: check if graph itself is the nodes array
            if (parsedContent.Data && 
                parsedContent.Data.RootChunk && 
                parsedContent.Data.RootChunk.graph &&
                Array.isArray(parsedContent.Data.RootChunk.graph)) {
                return parsedContent.Data.RootChunk.graph.length;
            }
        }
        
        // If we can't find nodes in expected locations, return 0 (will be processed)
        return 0;
        
    } catch (error) {
        Logger.Warning(`Error counting nodes in ${fileName}: ${error.message}`);
        return 0; // Return 0 to allow processing if we can't determine node count
    }
}

// ===== JSON STRING SEARCH FOR BETTER CONTEXT =====
function searchInJsonString(jsonString, searchString, results, fileName) {
    const lowerJson = jsonString.toLowerCase();
    const lowerSearch = searchString.toLowerCase();
    
    let index = 0;
    while ((index = lowerJson.indexOf(lowerSearch, index)) !== -1) {
        // Split context length evenly before and after the match
        const halfContext = Math.floor(CONTEXT_LENGTH / 2);
        const beforeContext = halfContext;
        const afterContext = CONTEXT_LENGTH - beforeContext; // Handle odd numbers
        
        // Calculate context boundaries
        const preContextStart = Math.max(0, index - beforeContext);
        const postContextEnd = Math.min(index + searchString.length + afterContext, jsonString.length);
        
        // Extract the full context
        const fullContext = jsonString.substring(preContextStart, postContextEnd);
        
        // Build the display string with ellipsis if needed
        const startEllipsis = preContextStart > 0 ? '...' : '';
        const endEllipsis = postContextEnd < jsonString.length ? '...' : '';
        
        results.count++;
        results.contexts.push({
            path: "[Raw JSON]",
            value: `${startEllipsis}${fullContext}${endEllipsis}`,
            fullMatch: fullContext,
            matchPosition: index,
            contextLength: CONTEXT_LENGTH,
            beforeChars: index - preContextStart,
            afterChars: postContextEnd - (index + searchString.length)
        });
        
        index += searchString.length; // Move past this match
    }
}

// ===== RECURSIVE SEARCH FUNCTION WITH CONTEXT =====
function searchInObject(obj, searchString, results, fileName, currentPath = "", lowerFileName = "") {
    // Performance optimization: skip large sections that are usually not relevant for .scene files
    if (IGNOREIDANDLOCSTORE && lowerFileName.endsWith('.scene')) {
        const pathLower = currentPath.toLowerCase();
        // Skip debugSymbols (ordinal 25) and locStore (ordinal 15) sections in scene files
        // These are top-level properties: Data.RootChunk.debugSymbols and Data.RootChunk.locStore
        if (pathLower === 'data.rootchunk.debugsymbols' || 
            pathLower === 'data.rootchunk.locstore' ||
            pathLower.startsWith('data.rootchunk.debugsymbols.') ||
            pathLower.startsWith('data.rootchunk.locstore.')) {
            // Skip these sections entirely for performance
            // Logger.Debug(`Skipping section for performance: ${currentPath}`);
            return;
        }
    }
    if (typeof obj === 'string') {
        // Direct string search with bidirectional context extraction
        const lowerObj = obj.toLowerCase();
        const lowerSearch = searchString.toLowerCase();
        
        let index = 0;
        while ((index = lowerObj.indexOf(lowerSearch, index)) !== -1) {
            // Split context length evenly before and after the match
            const halfContext = Math.floor(CONTEXT_LENGTH / 2);
            const beforeContext = halfContext;
            const afterContext = CONTEXT_LENGTH - beforeContext; // Handle odd numbers
            
            // Calculate context boundaries
            const preContextStart = Math.max(0, index - beforeContext);
            const postContextEnd = Math.min(index + searchString.length + afterContext, obj.length);
            
            // Extract the full context
            const fullContext = obj.substring(preContextStart, postContextEnd);
            
            // Build the display string with ellipsis if needed
            const startEllipsis = preContextStart > 0 ? '...' : '';
            const endEllipsis = postContextEnd < obj.length ? '...' : '';
            
            results.count++;
            results.contexts.push({
                path: currentPath,
                value: `${startEllipsis}${fullContext}${endEllipsis}`,
                fullMatch: fullContext,
                matchPosition: index,
                contextLength: CONTEXT_LENGTH,
                beforeChars: index - preContextStart,
                afterChars: postContextEnd - (index + searchString.length)
            });
            
            index += searchString.length; // Move past this match
        }
        
    } else if (Array.isArray(obj)) {
        // Handle arrays
        for (let i = 0; i < obj.length; i++) {
            const newPath = currentPath ? `${currentPath}[${i}]` : `[${i}]`;
            searchInObject(obj[i], searchString, results, fileName, newPath, lowerFileName);
        }
    } else if (typeof obj === 'object' && obj !== null) {
        // Handle objects
        for (const key in obj) {
            if (obj.hasOwnProperty(key)) {
                // Check if the key itself contains our search string
                const lowerKey = key.toLowerCase();
                const lowerSearch = searchString.toLowerCase();
                
                if (lowerKey.includes(lowerSearch)) {
                    // For property names, show the key and try to show some of the value
                    let valuePreview = "";
                    try {
                        // Use half the context length for value preview since we're showing key + value
                        const valueContextLength = Math.floor(CONTEXT_LENGTH / 2);
                        if (typeof obj[key] === 'string') {
                            valuePreview = obj[key].substring(0, valueContextLength);
                        } else if (typeof obj[key] === 'object') {
                            valuePreview = JSON.stringify(obj[key]).substring(0, valueContextLength);
                        } else {
                            valuePreview = String(obj[key]);
                        }
                    } catch (e) {
                        valuePreview = "[Unable to preview value]";
                    }
                    
                    const keyValuePair = `${key}: ${valuePreview}`;
                    const hasMoreValue = (typeof obj[key] === 'string' && obj[key].length > Math.floor(CONTEXT_LENGTH / 2)) ||
                                       (typeof obj[key] === 'object' && JSON.stringify(obj[key]).length > Math.floor(CONTEXT_LENGTH / 2));
                    
                    results.count++;
                    results.contexts.push({
                        path: currentPath ? `${currentPath}.${key}` : key,
                        value: `${keyValuePair}${hasMoreValue ? '...' : ''}`,
                        fullMatch: keyValuePair,
                        matchPosition: 0,
                        contextLength: CONTEXT_LENGTH,
                        beforeChars: 0,
                        afterChars: valuePreview.length
                    });
                }
                
                // Recursively search the value
                const newPath = currentPath ? `${currentPath}.${key}` : key;
                searchInObject(obj[key], searchString, results, fileName, newPath, lowerFileName);
            }
        }
    }
}

// ===== RESULTS GENERATION =====
function generateResults(state) {
    const endTime = Date.now();
    const duration = Math.round((endTime - state.startTime) / 1000);
    
    Logger.Info("=== Search Results ===");
    Logger.Info(`Search string: "${SEARCH_STRING}"`);
    Logger.Info(`Context length: ${CONTEXT_LENGTH} characters (bidirectional)`);
    Logger.Info(`Files processed: ${state.processedFiles}`);
    Logger.Info(`Files skipped (too many nodes): ${state.skippedFiles}`);
    Logger.Info(`Files with matches: ${state.matchingFiles.length}`);
    Logger.Info(`Total matches found: ${state.totalMatches}`);
    Logger.Info(`Errors encountered: ${state.errors.length}`);
    Logger.Info(`Duration: ${duration} seconds`);
    
    // Generate detailed report
    let reportContent = generateDetailedReport(state, duration);
    
    // Save report to raw folder
    const reportFileName = `search_context_${SEARCH_STRING.replace(/[^a-zA-Z0-9]/g, '_')}_${Date.now()}.txt`;
    try {
        wkit.SaveToRaw(reportFileName, reportContent);
        Logger.Info(`Detailed report saved to: ${reportFileName}`);
    } catch (error) {
        Logger.Error(`Could not save report: ${error.message}`);
    }
    
    // Show completion message
    const message = `String Search with Context Complete!\n\n` +
                   `Search string: "${SEARCH_STRING}"\n` +
                   `Context length: ${CONTEXT_LENGTH} characters (bidirectional)\n` +
                   `Files processed: ${state.processedFiles}\n` +
                   `Files skipped (too many nodes): ${state.skippedFiles}\n` +
                   `Files with matches: ${state.matchingFiles.length}\n` +
                   `Total matches: ${state.totalMatches}\n` +
                   `Duration: ${duration}s\n\n` +
                   `Detailed report saved to raw folder:\n${reportFileName}`;
    
    wkit.ShowMessageBox(message, "Search Complete", 0, 0);
}

function generateDetailedReport(state, duration) {
    let report = "Archive File String Search with Context Report\n";
    report += "=".repeat(60) + "\n\n";
    report += `Generated: ${new Date().toISOString()}\n`;
    report += `Search String: "${SEARCH_STRING}"\n`;
    report += `Context Length: ${CONTEXT_LENGTH} characters (bidirectional)\n`;
    report += `Files Processed: ${state.processedFiles}\n`;
    report += `Files Skipped (too many nodes): ${state.skippedFiles}\n`;
    report += `Files with Matches: ${state.matchingFiles.length}\n`;
    report += `Total Matches: ${state.totalMatches}\n`;
    report += `Duration: ${duration} seconds\n\n`;
    
    if (state.matchingFiles.length > 0) {
        report += "MATCHING FILES WITH CONTEXT:\n";
        report += "-".repeat(40) + "\n\n";
        
        for (const match of state.matchingFiles) {
            report += `File: ${match.fileName}\n`;
            report += `Matches: ${match.matchCount}\n`;
            
            if (match.contexts.length > 0) {
                report += "Contexts found:\n";
                for (let i = 0; i < match.contexts.length; i++) {
                    const context = match.contexts[i];
                    report += `  ${i + 1}. Path: ${context.path}\n`;
                    report += `     Context: ${context.value}\n`;
                    if (context.matchPosition !== undefined) {
                        report += `     Position: ${context.matchPosition}\n`;
                    }
                    report += "\n";
                }
            }
            report += "-".repeat(40) + "\n\n";
        }
    }
    
    if (state.errors.length > 0) {
        report += "\nERRORS ENCOUNTERED:\n";
        report += "-".repeat(30) + "\n\n";
        for (const error of state.errors) {
            report += `${error}\n`;
        }
    }
    
    return report;
}

// Start the search
main(); 
