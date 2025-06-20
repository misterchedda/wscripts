// Search for string in quest phases and scene files directly from archives
// @author MisterChedda
// @version 1.0
// Searches all .questphase and .scene files in game archives for a given string
// No need to add files to project first!

import * as Logger from 'Logger.wscript';
import * as TypeHelper from 'TypeHelper.wscript';

// ===== CONFIGURATION =====
const SEARCH_STRING = "TeleportPuppet"; // Change this to search for different strings
const INCLUDE_QUESTPHASE = true;       // Search in .questphase files
const INCLUDE_SCENE = true;            // Search in .scene files
const MAX_FILES_TO_PROCESS = 250;     // Limit to prevent memory issues
const SHOW_PROGRESS_EVERY = 5;        // Show progress every N files

// ===== MAIN FUNCTION =====
function main() {
    Logger.Info("=== Archive File String Search ===");
    Logger.Info(`Searching for: "${SEARCH_STRING}"`);
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
            
            // Prevent memory issues
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
            
            // Search for string in the parsed content
            const searchResults = { count: 0, contexts: [] };
            searchInObject(parsedContent, SEARCH_STRING, searchResults, gameFile.FileName);
            
            if (searchResults.count > 0) {
                state.matchingFiles.push({
                    fileName: gameFile.FileName,
                    matchCount: searchResults.count,
                    contexts: searchResults.contexts.slice(0, 5) // Limit contexts to first 5
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

// ===== RECURSIVE SEARCH FUNCTION =====
function searchInObject(obj, searchString, results, fileName, currentPath = "") {
    if (typeof obj === 'string') {
        // Direct string search
        const lowerObj = obj.toLowerCase();
        const lowerSearch = searchString.toLowerCase();
        
        if (lowerObj.includes(lowerSearch)) {
            results.count++;
            results.contexts.push({
                path: currentPath,
                value: obj.length > 200 ? obj.substring(0, 200) + "..." : obj,
                fullMatch: obj
            });
        }
    } else if (Array.isArray(obj)) {
        // Handle arrays
        for (let i = 0; i < obj.length; i++) {
            const newPath = currentPath ? `${currentPath}[${i}]` : `[${i}]`;
            searchInObject(obj[i], searchString, results, fileName, newPath);
        }
    } else if (typeof obj === 'object' && obj !== null) {
        // Handle objects
        for (const key in obj) {
            if (obj.hasOwnProperty(key)) {
                // Check if the key itself contains our search string
                const lowerKey = key.toLowerCase();
                const lowerSearch = searchString.toLowerCase();
                
                if (lowerKey.includes(lowerSearch)) {
                    results.count++;
                    results.contexts.push({
                        path: currentPath ? `${currentPath}.${key}` : key,
                        value: `[Property name: ${key}]`,
                        fullMatch: key
                    });
                }
                
                // Recursively search the value
                const newPath = currentPath ? `${currentPath}.${key}` : key;
                searchInObject(obj[key], searchString, results, fileName, newPath);
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
    Logger.Info(`Files processed: ${state.processedFiles}`);
    Logger.Info(`Files with matches: ${state.matchingFiles.length}`);
    Logger.Info(`Total matches found: ${state.totalMatches}`);
    Logger.Info(`Errors encountered: ${state.errors.length}`);
    Logger.Info(`Duration: ${duration} seconds`);
    
    // Generate detailed report
    let reportContent = generateDetailedReport(state, duration);
    
    // Save report to raw folder
    const reportFileName = `search_results_${SEARCH_STRING.replace(/[^a-zA-Z0-9]/g, '_')}_${Date.now()}.txt`;
    try {
        wkit.SaveToRaw(reportFileName, reportContent);
        Logger.Info(`Detailed report saved to: ${reportFileName}`);
    } catch (error) {
        Logger.Error(`Could not save report: ${error.message}`);
    }
    
    // Show completion message
    const message = `String Search Complete!\n\n` +
                   `Search string: "${SEARCH_STRING}"\n` +
                   `Files processed: ${state.processedFiles}\n` +
                   `Files with matches: ${state.matchingFiles.length}\n` +
                   `Total matches: ${state.totalMatches}\n` +
                   `Duration: ${duration}s\n\n` +
                   `Detailed report saved to raw folder:\n${reportFileName}`;
    
    wkit.ShowMessageBox(message, "Search Complete", 0, 0);
}

function generateDetailedReport(state, duration) {
    let report = "Archive File String Search Report\n";
    report += "=".repeat(50) + "\n\n";
    report += `Generated: ${new Date().toISOString()}\n`;
    report += `Search String: "${SEARCH_STRING}"\n`;
    report += `Files Processed: ${state.processedFiles}\n`;
    report += `Files with Matches: ${state.matchingFiles.length}\n`;
    report += `Total Matches: ${state.totalMatches}\n`;
    report += `Duration: ${duration} seconds\n\n`;
    
    if (state.matchingFiles.length > 0) {
        report += "MATCHING FILES:\n";
        report += "-".repeat(30) + "\n\n";
        
        for (const match of state.matchingFiles) {
            report += `File: ${match.fileName}\n`;
            report += `Matches: ${match.matchCount}\n`;
            
            if (match.contexts.length > 0) {
                report += "Sample contexts:\n";
                for (let i = 0; i < Math.min(3, match.contexts.length); i++) {
                    const context = match.contexts[i];
                    report += `  - Path: ${context.path}\n`;
                    report += `    Value: ${context.value}\n`;
                }
            }
            report += "\n";
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
