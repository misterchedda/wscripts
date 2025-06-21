// Search for string in .anims files with customizable path filtering directly from archives
// @author MisterChedda
// @version 1.2
// Searches .anims files in game archives based on customizable include/exclude path terms
// Configure INCLUDE_PATH_TERMS, EXCLUDE_PATH_TERMS, and RIG_FILTER_TERMS arrays to control which files to search
// Now focuses specifically on animation names and provides duration info
// No need to add files to project first!

import * as Logger from 'Logger.wscript';
import * as TypeHelper from 'TypeHelper.wscript';

// ===== CONFIGURATION =====
const SEARCH_STRING = "faint"; // Change this to search for different strings
const SHOW_PROGRESS_EVERY = 500;        // Show progress every N files
const VERBOSE_LOGGING = false;         // Set to true for detailed per-file logging, false for minimal output

// Path filtering - customize these arrays to control which .anims files to search
const INCLUDE_PATH_TERMS = ["quest"];  // If ANY of these terms are in the path, include the file
const EXCLUDE_PATH_TERMS = ["lipsync"];         // If ANY of these terms are in the path, exclude the file

// Rig filtering - if empty, searches all anim. If terms provided, only searches anims with matching entire rig paths (as linked in the .anims file)
const RIG_FILTER_TERMS = [];     // Example: ["woman", "wa"] - if ANY of these terms are in the rig path, include the file
                                    

// ===== MAIN FUNCTION =====
function main() {
    Logger.Info("=== .anims Files Animation Name Search ===");
    Logger.Info(`Searching for: "${SEARCH_STRING}"`);
    Logger.Info(`Include path terms: [${INCLUDE_PATH_TERMS.join(', ')}]`);
    Logger.Info(`Exclude path terms: [${EXCLUDE_PATH_TERMS.join(', ')}]`);
    Logger.Info(`Rig filter terms: [${RIG_FILTER_TERMS.length > 0 ? RIG_FILTER_TERMS.join(', ') : 'ALL RIGS'}]`);
    
    const state = initializeState();
    
    try {
        // Phase 1: Collect target files from archives
        Logger.Info("Phase 1: Collecting .anims files based on path and rig filters from game archives...");
        collectTargetFiles(state);
        
        if (state.targetFiles.length === 0) {
            Logger.Warning("No .anims files matching filters found in archives!");
            return;
        }
        
        Logger.Info(`Found ${state.targetFiles.length} target .anims files`);
        
        // Phase 2: Search through animation names
        Logger.Info("Phase 2: Searching animation names for string...");
        searchAnimationNames(state);
        
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
        matchingAnimations: [],
        totalMatches: 0,
        errors: [],
        startTime: Date.now()
    };
}

// ===== FILE COLLECTION =====
function collectTargetFiles(state) {
    Logger.Info("Scanning game archives for .anims files based on path and rig filters...");
    
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
        
        // Check if file should be excluded based on path
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
        
        // Check if file should be included based on path
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
        
        if (!shouldInclude) {
            continue;
        }
        
        // If rig filter is specified, check the rig field
        if (RIG_FILTER_TERMS.length > 0) {
            if (!checkRigFilter(gameFile)) {
                continue;
            }
        }
        
        state.targetFiles.push(gameFile);
        fileCount++;
    }
    
    Logger.Info(`Collected ${fileCount} target .anims files for processing`);
}

// ===== HELPER FUNCTIONS =====
function extractCNameValue(cNameObj) {
    if (!cNameObj) {
        return null;
    }
    
    // If it's already a string, return it
    if (typeof cNameObj === 'string') {
        return cNameObj;
    }
    
    // Handle CName object structure - common patterns in WolvenKit JSON
    if (cNameObj.$storage) {
        return cNameObj.$storage;
    }
    
    if (cNameObj.$value) {
        return cNameObj.$value;
    }
    
    if (cNameObj.value) {
        return cNameObj.value;
    }
    
    // If it has a Data property, try that
    if (cNameObj.Data && typeof cNameObj.Data === 'string') {
        return cNameObj.Data;
    }
    
    // Last resort: convert to string and see if it looks reasonable
    const str = String(cNameObj);
    if (str && str !== '[object Object]' && str.length > 0) {
        return str;
    }
    
    return null;
}

// ===== RIG FILTER CHECK =====
function checkRigFilter(gameFile) {
    try {
        // Load file content as JSON to check rig field
        const fileContent = wkit.GameFileToJson(gameFile);
        if (!fileContent) {
            return false;
        }
        
        let parsedContent;
        try {
            parsedContent = TypeHelper.JsonParse(fileContent);
        } catch (parseError) {
            return false;
        }
        
        if (!parsedContent || !parsedContent.Data || !parsedContent.Data.RootChunk) {
            return false;
        }
        
        const rigPath = parsedContent.Data.RootChunk.rig?.DepotPath;
        if (!rigPath) {
            return false; // No rig path found
        }
        
        const rigPathLower = rigPath.toLowerCase();
        
        // Check if any rig filter term matches
        for (const rigTerm of RIG_FILTER_TERMS) {
            if (rigPathLower.includes(rigTerm.toLowerCase())) {
                return true;
            }
        }
        
        return false;
        
    } catch (error) {
        if (VERBOSE_LOGGING) {
            Logger.Warning(`Error checking rig filter for ${gameFile.FileName}: ${error.message}`);
        }
        return false;
    }
}

// ===== ANIMATION NAME SEARCHING =====
function searchAnimationNames(state) {
    let processed = 0;
    
    for (const gameFile of state.targetFiles) {
        try {
            processed++;
            
            // Progress update
            if (processed % SHOW_PROGRESS_EVERY === 0) {
                Logger.Info(`Progress: ${processed}/${state.targetFiles.length} files processed (${state.matchingAnimations.length} matches so far)`);
            }
            
            // Load file content as JSON using the GameFile object directly
            const fileContent = wkit.GameFileToJson(gameFile);
            if (!fileContent) {
                if (VERBOSE_LOGGING) {
                    Logger.Warning(`Could not load content for: ${gameFile.FileName}`);
                }
                state.errors.push(`Failed to load: ${gameFile.FileName}`);
                continue;
            }
            
            // Parse JSON
            let parsedContent;
            try {
                parsedContent = TypeHelper.JsonParse(fileContent);
            } catch (parseError) {
                if (VERBOSE_LOGGING) {
                    Logger.Warning(`Could not parse JSON for: ${gameFile.FileName}`);
                }
                state.errors.push(`Failed to parse: ${gameFile.FileName} - ${parseError.message}`);
                continue;
            }
            
            if (!parsedContent || !parsedContent.Data || !parsedContent.Data.RootChunk) {
                continue;
            }
            
            const rootChunk = parsedContent.Data.RootChunk;
            
            // Get rig path for reporting
            const rigPath = rootChunk.rig?.DepotPath || "Unknown";
            
            // Check animations array
            if (!rootChunk.animations || !Array.isArray(rootChunk.animations)) {
                if (VERBOSE_LOGGING) {
                    Logger.Debug(`No animations array found in ${gameFile.FileName}`);
                }
                continue;
            }
            
            if (VERBOSE_LOGGING) {
                Logger.Debug(`Processing ${gameFile.FileName}: ${rootChunk.animations.length} animations, rig: ${rigPath}`);
            }
            
            // Search through each animation for name matches
            let fileMatches = 0;
            for (let i = 0; i < rootChunk.animations.length; i++) {
                const animEntry = rootChunk.animations[i];
                
                if (!animEntry || !animEntry.Data || !animEntry.Data.animation || !animEntry.Data.animation.Data) {
                    continue;
                }
                
                const animation = animEntry.Data.animation.Data;
                const animNameObj = animation.name;
                const animDuration = animation.duration || 0;
                
                if (!animNameObj) {
                    continue;
                }
                
                // Extract string value from CName object
                const animName = extractCNameValue(animNameObj);
                if (!animName) {
                    continue;
                }
                
                // Check if animation name contains search string
                if (animName.toLowerCase().includes(SEARCH_STRING.toLowerCase())) {
                    state.matchingAnimations.push({
                        fileName: gameFile.FileName,
                        rigPath: rigPath,
                        animationName: animName,
                        duration: animDuration,
                        animationIndex: i
                    });
                    
                    fileMatches++;
                                         state.totalMatches++;
                     
                     if (VERBOSE_LOGGING) {
                         Logger.Info(`MATCH: ${gameFile.FileName} [${i}] - Name: "${animName}", Duration: ${animDuration}s`);
                     }
                 }
             }
             
             if (fileMatches > 0) {
                 Logger.Info(`File ${gameFile.FileName}: ${fileMatches} matching animations found`);
             }
            
        } catch (error) {
            if (VERBOSE_LOGGING) {
                Logger.Error(`Error processing ${gameFile.FileName}: ${error.message}`);
            }
            state.errors.push(`Error processing ${gameFile.FileName}: ${error.message}`);
        }
    }
    
    state.processedFiles = processed;
}

// ===== RESULTS GENERATION =====
function generateResults(state) {
    const endTime = Date.now();
    const duration = Math.round((endTime - state.startTime) / 1000);
    
    Logger.Info("=== Search Results ===");
    Logger.Info(`Search string: "${SEARCH_STRING}"`);
    Logger.Info(`Files processed: ${state.processedFiles}`);
    Logger.Info(`Matching animations found: ${state.totalMatches}`);
    Logger.Info(`Files with matches: ${[...new Set(state.matchingAnimations.map(m => m.fileName))].length}`);
    Logger.Info(`Errors encountered: ${state.errors.length}`);
    Logger.Info(`Duration: ${duration} seconds`);
    
    // Generate detailed report
    let reportContent = generateDetailedReport(state, duration);
    
    // Save report to raw folder
    const reportFileName = `anims_name_search_${SEARCH_STRING.replace(/[^a-zA-Z0-9]/g, '_')}_${Date.now()}.txt`;
    try {
        wkit.SaveToRaw(reportFileName, reportContent);
        Logger.Info(`Detailed report saved to: ${reportFileName}`);
    } catch (error) {
        Logger.Error(`Could not save report: ${error.message}`);
    }
    
    // Show completion message
    const uniqueFiles = [...new Set(state.matchingAnimations.map(m => m.fileName))].length;
    const message = `.anims Animation Name Search Complete!\n\n` +
                   `Search string: "${SEARCH_STRING}"\n` +
                   `Include terms: [${INCLUDE_PATH_TERMS.join(', ')}]\n` +
                   `Exclude terms: [${EXCLUDE_PATH_TERMS.join(', ')}]\n` +
                   `Rig filter: [${RIG_FILTER_TERMS.length > 0 ? RIG_FILTER_TERMS.join(', ') : 'ALL RIGS'}]\n` +
                   `Files processed: ${state.processedFiles}\n` +
                   `Files with matches: ${uniqueFiles}\n` +
                   `Total matching animations: ${state.totalMatches}\n` +
                   `Duration: ${duration}s\n\n` +
                   `Detailed report saved to raw folder:\n${reportFileName}`;
    
    wkit.ShowMessageBox(message, "Search Complete", 0, 0);
}

function generateDetailedReport(state, duration) {
    let report = ".anims Animation Name Search Report\n";
    report += "=".repeat(60) + "\n\n";
    report += `Generated: ${new Date().toISOString()}\n`;
    report += `Search String: "${SEARCH_STRING}"\n`;
    report += `Include Path Terms: [${INCLUDE_PATH_TERMS.join(', ')}]\n`;
    report += `Exclude Path Terms: [${EXCLUDE_PATH_TERMS.join(', ')}]\n`;
    report += `Rig Filter Terms: [${RIG_FILTER_TERMS.length > 0 ? RIG_FILTER_TERMS.join(', ') : 'ALL RIGS'}]\n`;
    report += `Files Processed: ${state.processedFiles}\n`;
    report += `Total Matching Animations: ${state.totalMatches}\n`;
    report += `Files with Matches: ${[...new Set(state.matchingAnimations.map(m => m.fileName))].length}\n`;
    report += `Duration: ${duration} seconds\n\n`;
    
    if (state.matchingAnimations.length > 0) {
        report += "MATCHING ANIMATIONS:\n";
        report += "-".repeat(40) + "\n\n";
        
        // Group by file for better organization
        const fileGroups = {};
        for (const match of state.matchingAnimations) {
            if (!fileGroups[match.fileName]) {
                fileGroups[match.fileName] = [];
            }
            fileGroups[match.fileName].push(match);
        }
        
        for (const [fileName, matches] of Object.entries(fileGroups)) {
            report += `File: ${fileName}\n`;
            if (matches.length > 0) {
                report += `Rig: ${matches[0].rigPath}\n`;
            }
            report += `Matching Animations (${matches.length}):\n`;
            
            for (const match of matches) {
                report += `  [${match.animationIndex}] "${match.animationName}" (${match.duration}s)\n`;
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
