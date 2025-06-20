// Search for string in .anims files with customizable path filtering directly from archives
// @author MisterChedda
// @version 1.1
// Searches .anims files in game archives based on customizable include/exclude path terms
// Configure INCLUDE_PATH_TERMS and EXCLUDE_PATH_TERMS arrays to control which files to search
// No need to add files to project first!

import * as Logger from 'Logger.wscript';
import * as TypeHelper from 'TypeHelper.wscript';

// ===== CONFIGURATION =====
const SEARCH_STRING = "faint"; // Change this to search for different strings
const MAX_FILES_TO_PROCESS = 1000;     // Max files to search
const SHOW_PROGRESS_EVERY = 100;        // Show progress every N files

// Path filtering - customize these arrays to control which .anims files to search
const INCLUDE_PATH_TERMS = ["quest"];  // If ANY of these terms are in the path, include the file
const EXCLUDE_PATH_TERMS = ["lipsync"];         // If ANY of these terms are in the path, exclude the file
                                    

// ===== MAIN FUNCTION =====
function main() {
    Logger.Info("=== .anims Files Path-Filtered String Search ===");
    Logger.Info(`Searching for: "${SEARCH_STRING}"`);
    Logger.Info(`Include path terms: [${INCLUDE_PATH_TERMS.join(', ')}]`);
    Logger.Info(`Exclude path terms: [${EXCLUDE_PATH_TERMS.join(', ')}]`);
    
    const state = initializeState();
    
    try {
        // Phase 1: Collect target files from archives
        Logger.Info("Phase 1: Collecting .anims files based on path filters from game archives...");
        collectTargetFiles(state);
        
        if (state.targetFiles.length === 0) {
            Logger.Warning("No .anims files matching path filters found in archives!");
            return;
        }
        
        Logger.Info(`Found ${state.targetFiles.length} target .anims files`);
        
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
    Logger.Info("Scanning game archives for .anims files based on path filters...");
    
    let fileCount = 0;
    const archiveFiles = wkit.GetArchiveFiles();
    
    for (const gameFile of archiveFiles) {
        if (!gameFile || !gameFile.FileName) {
            continue;
        }
        
        const fileName = gameFile.FileName.toLowerCase();
        
        // Check if it's a .anims file
        if (!fileName.endsWith('.anims')) {
            continue;
        }
        
        // Check if file should be excluded
        let shouldExclude = false;
        for (const excludeTerm of EXCLUDE_PATH_TERMS) {
            if (fileName.includes(excludeTerm.toLowerCase())) {
                shouldExclude = true;
                break;
            }
        }
        
        if (shouldExclude) {
            continue;
        }
        
        // Check if file should be included
        let shouldInclude = false;
        if (INCLUDE_PATH_TERMS.length === 0) {
            // If no include terms specified, include all non-excluded files
            shouldInclude = true;
        } else {
            for (const includeTerm of INCLUDE_PATH_TERMS) {
                if (fileName.includes(includeTerm.toLowerCase())) {
                    shouldInclude = true;
                    break;
                }
            }
        }
        
        if (shouldInclude) {
            state.targetFiles.push(gameFile);
            fileCount++;
            
            if (fileCount >= MAX_FILES_TO_PROCESS) {
                Logger.Warning(`Reached maximum file limit (${MAX_FILES_TO_PROCESS}). Some files may be skipped.`);
                break;
            }
        }
    }
    
    Logger.Info(`Collected ${fileCount} target .anims files for processing`);
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
            
            // Get animation count for reporting
            const animCount = getAnimationCount(parsedContent, gameFile.FileName);
            
            if (animCount > 0) {
                Logger.Debug(`Processing ${gameFile.FileName}: ${animCount} animations`);
            }
            
            // Search for string in the parsed content
            const searchResults = { count: 0, contexts: [] };
            searchInObject(parsedContent, SEARCH_STRING, searchResults, gameFile.FileName);
            
            if (searchResults.count > 0) {
                state.matchingFiles.push({
                    fileName: gameFile.FileName,
                    matchCount: searchResults.count,
                    animationCount: animCount,
                    contexts: searchResults.contexts.slice(0, 5) // Limit contexts to first 5
                });
                
                state.totalMatches += searchResults.count;
                Logger.Info(`MATCH: ${gameFile.FileName}: ${searchResults.count} instance(s) in ${animCount} animations`);
            }
            
        } catch (error) {
            Logger.Error(`Error processing ${gameFile.FileName}: ${error.message}`);
            state.errors.push(`Error processing ${gameFile.FileName}: ${error.message}`);
        }
    }
    
    state.processedFiles = processed;
}

// ===== ANIMATION COUNTING FUNCTION =====
function getAnimationCount(parsedContent, fileName) {
    try {
        // .anims files: animations are in Data.RootChunk.animations array
        if (parsedContent.Data && 
            parsedContent.Data.RootChunk && 
            parsedContent.Data.RootChunk.animations &&
            Array.isArray(parsedContent.Data.RootChunk.animations)) {
            return parsedContent.Data.RootChunk.animations.length;
        }
        
        // If we can't find animations in expected location, return 0 (will be processed)
        return 0;
        
    } catch (error) {
        Logger.Warning(`Error counting animations in ${fileName}: ${error.message}`);
        return 0; // Return 0 to allow processing if we can't determine animation count
    }
}

// ===== RECURSIVE SEARCH FUNCTION =====
function searchInObject(obj, searchString, results, fileName, currentPath = "") {
    // Skip searching in binary animation data to avoid false positives
    if (currentPath.includes('animationDataChunks') && currentPath.endsWith('buffer.Bytes')) {
        return; // Skip binary data
    }
    
    // Skip searching in animation buffer data to avoid false positives
    if (currentPath.includes('animations') && currentPath.endsWith('tempBuffer.Bytes')) {
        return; // Skip binary animation buffer data
    }
    
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
    const reportFileName = `anims_search_${SEARCH_STRING.replace(/[^a-zA-Z0-9]/g, '_')}_${Date.now()}.txt`;
    try {
        wkit.SaveToRaw(reportFileName, reportContent);
        Logger.Info(`Detailed report saved to: ${reportFileName}`);
    } catch (error) {
        Logger.Error(`Could not save report: ${error.message}`);
    }
    
    // Show completion message
    const message = `.anims Files String Search Complete!\n\n` +
                   `Search string: "${SEARCH_STRING}"\n` +
                   `Include terms: [${INCLUDE_PATH_TERMS.join(', ')}]\n` +
                   `Exclude terms: [${EXCLUDE_PATH_TERMS.join(', ')}]\n` +
                   `Files processed: ${state.processedFiles}\n` +
                   `Files with matches: ${state.matchingFiles.length}\n` +
                   `Total matches: ${state.totalMatches}\n` +
                   `Duration: ${duration}s\n\n` +
                   `Detailed report saved to raw folder:\n${reportFileName}`;
    
    wkit.ShowMessageBox(message, "Search Complete", 0, 0);
}

function generateDetailedReport(state, duration) {
    let report = ".anims Files Path-Filtered String Search Report\n";
    report += "=".repeat(60) + "\n\n";
    report += `Generated: ${new Date().toISOString()}\n`;
    report += `Search String: "${SEARCH_STRING}"\n`;
    report += `Include Path Terms: [${INCLUDE_PATH_TERMS.join(', ')}]\n`;
    report += `Exclude Path Terms: [${EXCLUDE_PATH_TERMS.join(', ')}]\n`;
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
            report += `Animations: ${match.animationCount}\n`;
            
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
