// Search for string in streamingsector noderefs directly from archives
// @author MisterChedda
// @version 1.2
// Searches all .streamingsector files in game archives for a given string in noderefs
// and extracts context around each match
// No need to add files to project first!
import * as Logger from 'Logger.wscript';
import * as TypeHelper from 'TypeHelper.wscript';

// ===== CONFIGURATION =====
const SEARCH_STRING = "worldTrafficSplineNodes"; // Change this to search for different strings in noderefs
const CONTEXT_LENGTH = 300;              // Total context characters (split evenly before/after the match)
const MAX_FILES_TO_PROCESS = 9999;      // File Limit

const SHOW_PROGRESS_EVERY = 1000;         // Show progress every N files
const MAX_NODES_PER_FILE = 999999;         // Skip files with more than N nodes in nodeData
const SEARCH_IN_NODEREFS_ARRAY = true;  // Search in Data.RootChunk.nodeRefs array
const SEARCH_IN_NODEDATA = false;        // Search in Data.RootChunk.nodeData.Data[x].QuestPrefabRefHash

// ===== FILENAME FILTER =====
const FILENAME_MUST_CONTAIN = "";   // Only search files whose path contains this string (case-insensitive). Set to "" to search all files.

// ===== BIGINT HANDLING UTILITIES =====
function safeJsonStringify(obj) {
    try {
        return JSON.stringify(obj, (key, value) => {
            // Convert BigInt to string for serialization
            if (typeof value === 'bigint') {
                return value.toString() + 'n'; // Add 'n' suffix to indicate it was a BigInt
            }
            return value;
        });
    } catch (error) {
        Logger.Warning(`JSON stringify failed: ${error.message}`);
        return String(obj); // Fallback to string conversion
    }
}

function safeStringify(value) {
    if (typeof value === 'string') {
        return value;
    } else if (typeof value === 'number') {
        return value.toString();
    } else if (typeof value === 'bigint') {
        return value.toString() + 'n'; // Add 'n' suffix to indicate it was a BigInt
    } else if (typeof value === 'object') {
        return safeJsonStringify(value);
    } else {
        return String(value);
    }
}

// ===== MAIN FUNCTION =====
function main() {
    Logger.Info("=== StreamingSector NodeRef String Search ===");
    Logger.Info(`Searching for: "${SEARCH_STRING}"`);
    Logger.Info(`Context length: ${CONTEXT_LENGTH} characters (bidirectional)`);
    Logger.Info(`Search in nodeRefs array: ${SEARCH_IN_NODEREFS_ARRAY}`);
    Logger.Info(`Search in nodeData: ${SEARCH_IN_NODEDATA}`);
    if (FILENAME_MUST_CONTAIN) {
        Logger.Info(`Filename filter: only files containing "${FILENAME_MUST_CONTAIN}"`);
    } else {
        Logger.Info(`Filename filter: disabled (searching all streamingsector files)`);
    }
    
    const state = initializeState();
    
    try {
        // Phase 1: Collect target files from archives
        Logger.Info("Phase 1: Collecting .streamingsector files from game archives...");
        collectTargetFiles(state);
        
        if (state.targetFiles.length === 0) {
            Logger.Warning("No .streamingsector files found in archives!");
            return;
        }
        
        Logger.Info(`Found ${state.targetFiles.length} streamingsector files`);
        
        // Phase 2: Search through files
        Logger.Info("Phase 2: Searching streamingsector files for string in noderefs...");
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
        filteredOutFiles: 0,  // Track files filtered out by FILENAME_MUST_CONTAIN
        matchingFiles: [],
        totalMatches: 0,
        errors: [],
        startTime: Date.now()
    };
}

// ===== FILE COLLECTION =====
function collectTargetFiles(state) {
    Logger.Info("Scanning game archives for .streamingsector files...");
    
    let fileCount = 0;
    let filteredOut = 0;
    const archiveFiles = wkit.GetArchiveFiles();
    const filterLower = FILENAME_MUST_CONTAIN.toLowerCase();
    
    for (const gameFile of archiveFiles) {
        if (!gameFile || !gameFile.FileName) {
            continue;
        }
        
        const fileName = gameFile.FileName.toLowerCase();
        
        if (fileName.endsWith('.streamingsector')) {
            // Apply filename filter if set
            if (FILENAME_MUST_CONTAIN && !fileName.includes(filterLower)) {
                filteredOut++;
                continue;
            }
            
            state.targetFiles.push(gameFile);
            fileCount++;
            
            if (fileCount >= MAX_FILES_TO_PROCESS) {
                Logger.Warning(`Reached maximum file limit (${MAX_FILES_TO_PROCESS}). Some files may be skipped.`);
                break;
            }
        }
    }
    
    state.filteredOutFiles = filteredOut;
    
    Logger.Info(`Collected ${fileCount} streamingsector files for processing`);
    if (FILENAME_MUST_CONTAIN) {
        Logger.Info(`Filtered out ${filteredOut} files not matching "${FILENAME_MUST_CONTAIN}"`);
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
                state.skippedFiles++;
                continue;
            }
            
            // Search for string in noderefs
            const searchResults = { count: 0, contexts: [] };
            
            // Search in nodeRefs array if enabled
            if (SEARCH_IN_NODEREFS_ARRAY) {
                searchInNodeRefsArray(parsedContent, SEARCH_STRING, searchResults, gameFile.FileName);
            }
            
            // Search in nodeData if enabled
            if (SEARCH_IN_NODEDATA) {
                searchInNodeData(parsedContent, SEARCH_STRING, searchResults, gameFile.FileName);
            }
            
            if (searchResults.count > 0) {
                state.matchingFiles.push({
                    fileName: gameFile.FileName,
                    matchCount: searchResults.count,
                    contexts: searchResults.contexts.slice(0, 20) // Limit contexts to first 20
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
        // For streamingsector files, count nodes in nodeData.Data array
        if (parsedContent.Data && 
            parsedContent.Data.RootChunk && 
            parsedContent.Data.RootChunk.nodeData &&
            parsedContent.Data.RootChunk.nodeData.Data &&
            Array.isArray(parsedContent.Data.RootChunk.nodeData.Data)) {
            return parsedContent.Data.RootChunk.nodeData.Data.length;
        }
        
        // If we can't find nodes in expected location, return 0 (will be processed)
        return 0;
        
    } catch (error) {
        Logger.Warning(`Error counting nodes in ${fileName}: ${error.message}`);
        return 0;
    }
}

// ===== SEARCH IN NODEREFS ARRAY =====
function searchInNodeRefsArray(parsedContent, searchString, results, fileName) {
    try {
        if (parsedContent.Data && 
            parsedContent.Data.RootChunk && 
            parsedContent.Data.RootChunk.nodeRefs &&
            Array.isArray(parsedContent.Data.RootChunk.nodeRefs)) {
            
            const nodeRefs = parsedContent.Data.RootChunk.nodeRefs;
            
            for (let i = 0; i < nodeRefs.length; i++) {
                const nodeRef = nodeRefs[i];
                if (!nodeRef) continue;
                
                // Check the $value field
                if (nodeRef.$value) {
                    checkNodeRefValue(nodeRef.$value, searchString, results, `Data.RootChunk.nodeRefs[${i}].$value`);
                }
                
                // Also check if there's a string representation somewhere
                const nodeRefString = safeJsonStringify(nodeRef);
                if (nodeRefString.toLowerCase().includes(searchString.toLowerCase())) {
                    results.count++;
                    results.contexts.push({
                        path: `Data.RootChunk.nodeRefs[${i}]`,
                        value: nodeRefString.substring(0, CONTEXT_LENGTH),
                        fullMatch: nodeRefString,
                        matchPosition: 0,
                        contextLength: CONTEXT_LENGTH,
                        beforeChars: 0,
                        afterChars: Math.min(nodeRefString.length, CONTEXT_LENGTH)
                    });
                }
            }
        }
    } catch (error) {
        Logger.Warning(`Error searching nodeRefs array in ${fileName}: ${error.message}`);
    }
}

// ===== SEARCH IN NODEDATA =====
function searchInNodeData(parsedContent, searchString, results, fileName) {
    try {
        if (parsedContent.Data && 
            parsedContent.Data.RootChunk && 
            parsedContent.Data.RootChunk.nodeData &&
            parsedContent.Data.RootChunk.nodeData.Data &&
            Array.isArray(parsedContent.Data.RootChunk.nodeData.Data)) {
            
            const nodes = parsedContent.Data.RootChunk.nodeData.Data;
            
            for (let i = 0; i < nodes.length; i++) {
                const node = nodes[i];
                if (!node || !node.QuestPrefabRefHash) continue;
                
                const questRef = node.QuestPrefabRefHash;
                
                // Check the $value field
                if (questRef.$value) {
                    checkNodeRefValue(questRef.$value, searchString, results, `Data.RootChunk.nodeData.Data[${i}].QuestPrefabRefHash.$value`);
                }
                
                // Also check the entire QuestPrefabRefHash object as string
                const questRefString = safeJsonStringify(questRef);
                if (questRefString.toLowerCase().includes(searchString.toLowerCase())) {
                    results.count++;
                    
                    // Include some node context (position, etc)
                    let nodeContext = `Node ${i} (Index: ${node.NodeIndex || 'N/A'})`;
                    if (node.Position) {
                        nodeContext += ` at position (${node.Position.X}, ${node.Position.Y}, ${node.Position.Z})`;
                    }
                    nodeContext += `: ${questRefString}`;
                    
                    results.contexts.push({
                        path: `Data.RootChunk.nodeData.Data[${i}].QuestPrefabRefHash`,
                        value: nodeContext.substring(0, CONTEXT_LENGTH),
                        fullMatch: nodeContext,
                        matchPosition: 0,
                        contextLength: CONTEXT_LENGTH,
                        beforeChars: 0,
                        afterChars: Math.min(nodeContext.length, CONTEXT_LENGTH)
                    });
                }
            }
        }
    } catch (error) {
        Logger.Warning(`Error searching nodeData in ${fileName}: ${error.message}`);
    }
}

// ===== CHECK NODEREF VALUE =====
function checkNodeRefValue(value, searchString, results, path) {
    let valueStr = safeStringify(value);
    
    if (valueStr.toLowerCase().includes(searchString.toLowerCase())) {
        const lowerStr = valueStr.toLowerCase();
        const lowerSearch = searchString.toLowerCase();
        const index = lowerStr.indexOf(lowerSearch);
        
        // Extract context with bidirectional approach
        const halfContext = Math.floor(CONTEXT_LENGTH / 2);
        const beforeContext = halfContext;
        const afterContext = CONTEXT_LENGTH - beforeContext;
        
        const preContextStart = Math.max(0, index - beforeContext);
        const postContextEnd = Math.min(index + searchString.length + afterContext, valueStr.length);
        
        const fullContext = valueStr.substring(preContextStart, postContextEnd);
        const startEllipsis = preContextStart > 0 ? '...' : '';
        const endEllipsis = postContextEnd < valueStr.length ? '...' : '';
        
        results.count++;
        results.contexts.push({
            path: path,
            value: `${startEllipsis}${fullContext}${endEllipsis}`,
            fullMatch: fullContext,
            matchPosition: index,
            contextLength: CONTEXT_LENGTH,
            beforeChars: index - preContextStart,
            afterChars: postContextEnd - (index + searchString.length)
        });
    }
}

// ===== RESULTS GENERATION =====
function generateResults(state) {
    const endTime = Date.now();
    const duration = Math.round((endTime - state.startTime) / 1000);
    
    Logger.Info("=== Search Results ===");
    Logger.Info(`Search string: "${SEARCH_STRING}"`);
    Logger.Info(`Context length: ${CONTEXT_LENGTH} characters (bidirectional)`);
    Logger.Info(`Filename filter: "${FILENAME_MUST_CONTAIN || '(none)'}"`);
    Logger.Info(`Files processed: ${state.processedFiles}`);
    Logger.Info(`Files filtered out by filename: ${state.filteredOutFiles}`);
    Logger.Info(`Files skipped (too many nodes): ${state.skippedFiles}`);
    Logger.Info(`Files with matches: ${state.matchingFiles.length}`);
    Logger.Info(`Total matches found: ${state.totalMatches}`);
    Logger.Info(`Errors encountered: ${state.errors.length}`);
    Logger.Info(`Duration: ${duration} seconds`);
    
    // Generate detailed report
    let reportContent = generateDetailedReport(state, duration);
    
    // Save report to raw folder
    const reportFileName = `search_streamingsector_noderefs_${SEARCH_STRING.replace(/[^a-zA-Z0-9]/g, '_')}_${Date.now()}.txt`;
    try {
        wkit.SaveToRaw(reportFileName, reportContent);
        Logger.Info(`Detailed report saved to: ${reportFileName}`);
    } catch (error) {
        Logger.Error(`Could not save report: ${error.message}`);
    }
    
    // Show completion message
    const message = `StreamingSector NodeRef Search Complete!\n\n` +
                   `Search string: "${SEARCH_STRING}"\n` +
                   `Filename filter: "${FILENAME_MUST_CONTAIN || '(none)'}"\n` +
                   `Context length: ${CONTEXT_LENGTH} characters (bidirectional)\n` +
                   `Files processed: ${state.processedFiles}\n` +
                   `Files filtered out by filename: ${state.filteredOutFiles}\n` +
                   `Files skipped (too many nodes): ${state.skippedFiles}\n` +
                   `Files with matches: ${state.matchingFiles.length}\n` +
                   `Total matches: ${state.totalMatches}\n` +
                   `Duration: ${duration}s\n\n` +
                   `Detailed report saved to raw folder:\n${reportFileName}`;
    
    wkit.ShowMessageBox(message, "Search Complete", 0, 0);
}

function generateDetailedReport(state, duration) {
    let report = "StreamingSector NodeRef String Search Report\n";
    report += "=".repeat(60) + "\n\n";
    report += `Generated: ${new Date().toISOString()}\n`;
    report += `Search String: "${SEARCH_STRING}"\n`;
    report += `Filename Filter: "${FILENAME_MUST_CONTAIN || '(none)'}"\n`;
    report += `Context Length: ${CONTEXT_LENGTH} characters (bidirectional)\n`;
    report += `Search in nodeRefs array: ${SEARCH_IN_NODEREFS_ARRAY}\n`;
    report += `Search in nodeData: ${SEARCH_IN_NODEDATA}\n`;
    report += `Files Processed: ${state.processedFiles}\n`;
    report += `Files Filtered Out by Filename: ${state.filteredOutFiles}\n`;
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
                report += "NodeRef contexts found:\n";
                for (let i = 0; i < match.contexts.length; i++) {
                    const context = match.contexts[i];
                    report += `  ${i + 1}. Path: ${context.path}\n`;
                    report += `     Context: ${context.value}\n`;
                    if (context.matchPosition !== undefined) {
                        report += `     Match Position: ${context.matchPosition}\n`;
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
