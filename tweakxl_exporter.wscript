// @version 1.0
// @author MisterChedda

/*
 * Recursive TweakDB Dependencies Export
 * 
 * This script recursively explores TweakDB dependencies starting from a specific record.
 * It finds all related records, record types, and namespaces, then exports everything to YAML.
 * 
 * Features:
 * - Configurable starting record
 * - Smart recursive dependency detection
 * - Organized output by record type
 * - Progress tracking and error handling
 * - Comprehensive summary report
 * 
 * Usage:
 * 1. Configure STARTING_RECORD below
 * 2. Make sure TweakDB is loaded (visit Tweak Browser first)
 * 3. Run the script
 */

// ===== CONFIGURATION =====
var STARTING_RECORD = "Items.Preset_Tomahawk_Default";
var MAX_DEPTH = 10;
var BATCH_SIZE = 100;
var MAX_RECORDS_PER_TYPE = 1000;
var COMPREHENSIVE_MODE = true;

// ===== MAIN FUNCTION =====
function main() {
    logger.Info("=== Starting Recursive TweakDB Export ===");
    logger.Info("Starting record: " + STARTING_RECORD);
    
    if (!validatePrerequisites()) {
        return;
    }
    
    var outputDir = setupOutputDirectory();
    if (!outputDir) {
        return;
    }
    
    var state = initializeState();
    
    try {
        // Phase 1: Recursive exploration
        logger.Info("Phase 1: Exploring dependencies recursively...");
        exploreRecursively(state);
        
        // Phase 2: Export to YAML
        logger.Info("Phase 2: Exporting to YAML files...");
        exportToYaml(state, outputDir);
        
        // Phase 3: Generate summary
        logger.Info("Phase 3: Generating summary...");
        generateSummary(state, outputDir);
        
        logger.Info("=== Export completed successfully! ===");
        
    } catch (error) {
        logger.Error("Fatal error during export: " + error.message);
        wkit.ShowMessageBox(
            "Export failed with error:\n" + error.message,
            "Export Error", 2, 0
        );
    }
}

// ===== VALIDATION =====
function validatePrerequisites() {
    logger.Info("Checking prerequisites...");
    
    if (typeof wkit.GetRecords !== 'function') {
        logger.Error("wkit.GetRecords function not available");
        wkit.ShowMessageBox(
            "TweakDB functions not available. Please ensure:\n" +
            "1. A project is loaded in WolvenKit\n" +
            "2. Visit the Tweak Browser first to load TweakDB",
            "Prerequisites Not Met", 2, 0
        );
        return false;
    }
    logger.Info("wkit.GetRecords is available");
    
    if (typeof wkit.GetRecord !== 'function') {
        logger.Error("wkit.GetRecord function not available");
        wkit.ShowMessageBox(
            "TweakDB GetRecord function not available. Please ensure:\n" +
            "1. A project is loaded in WolvenKit\n" +
            "2. Visit the Tweak Browser first to load TweakDB",
            "Prerequisites Not Met", 2, 0
        );
        return false;
    }
    logger.Info("wkit.GetRecord is available");
    
    if (!wkit.HasTDBID(STARTING_RECORD)) {
        logger.Error("Starting record not found: " + STARTING_RECORD);
        wkit.ShowMessageBox(
            "Starting record \"" + STARTING_RECORD + "\" not found in TweakDB.\n\nPlease check the record name and try again.",
            "Record Not Found", 2, 0
        );
        return false;
    }
    logger.Info("Starting record found: " + STARTING_RECORD);
    
    // Test getting the record
    try {
        var testRecord = wkit.GetRecord(STARTING_RECORD);
        if (!testRecord) {
            logger.Error("Could not retrieve starting record data");
            return false;
        }
        logger.Info("Successfully retrieved starting record data (length: " + testRecord.length + ")");
    } catch (error) {
        logger.Error("Error retrieving starting record: " + error.message);
        return false;
    }
    
    return true;
}

function setupOutputDirectory() {
    try {
        var outputDir = "TweakDB_Dependencies/" + sanitizeFilename(STARTING_RECORD);
        logger.Info("Output directory: " + outputDir);
        return outputDir;
        
    } catch (error) {
        logger.Error("Could not setup output directory: " + error.message);
        return null;
    }
}

// ===== STATE MANAGEMENT =====
function initializeState() {
    return {
        processedRecords: {},
        pendingRecords: [STARTING_RECORD],
        recordTypes: {},
        namespaces: {},
        exportedContent: {},
        currentDepth: 0,
        stats: {
            totalRecordsExported: 0,
            recordTypesFound: {},
            namespacesFound: {},
            startTime: Date.now()
        }
    };
}

// ===== RECURSIVE EXPLORATION =====
function exploreRecursively(state) {
    while (state.pendingRecords.length > 0 && state.currentDepth < MAX_DEPTH) {
        var currentBatch = state.pendingRecords.splice(0, BATCH_SIZE);
        logger.Info("Processing batch of " + currentBatch.length + " records at depth " + state.currentDepth);
        
        for (var i = 0; i < currentBatch.length; i++) {
            var recordPath = currentBatch[i];
            
            if (state.processedRecords[recordPath]) {
                continue;
            }
            
            try {
                var recordData = getRecordData(recordPath);
                if (recordData) {
                    state.processedRecords[recordPath] = true;
                    state.exportedContent[recordPath] = recordData;
                    state.stats.totalRecordsExported++;
                    
                    // Extract dependencies
                    var dependencies = extractDependencies(recordData);
                    if (dependencies.length > 0) {
                        logger.Info("Found " + dependencies.length + " dependencies in " + recordPath);
                    }
                    for (var j = 0; j < dependencies.length; j++) {
                        var dep = dependencies[j];
                        if (!state.processedRecords[dep] && state.pendingRecords.indexOf(dep) === -1) {
                            state.pendingRecords.push(dep);
                        }
                    }
                    
                    // Track record types and namespaces
                    trackRecordMetadata(recordData, recordPath, state);
                }
                
            } catch (error) {
                logger.Error("Error processing record " + recordPath + ": " + error.message);
            }
        }
        
        state.currentDepth++;
        
        // Progress update
        if (state.stats.totalRecordsExported % 100 === 0) {
            logger.Info("Processed " + state.stats.totalRecordsExported + " records so far...");
        }
    }
    
    logger.Info("Exploration complete. Found " + state.stats.totalRecordsExported + " records.");
}

function getRecordData(recordPath) {
    try {
        var recordJsonString = wkit.GetRecord(recordPath);
        
        if (!recordJsonString) {
            logger.Error("GetRecord returned null/empty for: " + recordPath);
            return null;
        }
        
        var parsedData = JSON.parse(recordJsonString);
        
        // Debug the first record to understand structure
        if (recordPath === STARTING_RECORD) {
            logger.Info("Debug structure for starting record: " + recordPath);
            logger.Info("Top-level keys: " + Object.keys(parsedData).join(", "));
            if (parsedData.Data) {
                logger.Info("Data keys: " + Object.keys(parsedData.Data).join(", "));
            }
            if (parsedData.RootChunk) {
                logger.Info("RootChunk keys: " + Object.keys(parsedData.RootChunk).join(", "));
            }
        }
        
        return parsedData;
        
    } catch (error) {
        logger.Error("Error getting record " + recordPath + ": " + error.message);
        logger.Error("Raw data preview: " + (recordJsonString ? recordJsonString.substring(0, 200) : "null"));
        return null;
    }
}

function extractDependencies(recordData) {
    var dependencies = [];
    
    try {
        // Try different possible structures
        if (recordData && recordData.Data) {
            extractDependenciesFromObject(recordData.Data, dependencies);
        } else if (recordData && recordData.RootChunk) {
            extractDependenciesFromObject(recordData.RootChunk, dependencies);
        } else if (recordData) {
            extractDependenciesFromObject(recordData, dependencies);
        }
        
        logger.Info("Dependency extraction complete. Found " + dependencies.length + " potential dependencies");
    } catch (error) {
        logger.Error("Error extracting dependencies: " + error.message);
    }
    
    return dependencies;
}

function extractDependenciesFromObject(obj, dependencies) {
    if (!obj || typeof obj !== 'object') {
        return;
    }
    
    for (var key in obj) {
        if (!obj.hasOwnProperty(key)) {
            continue;
        }
        
        var value = obj[key];
        
        if (typeof value === 'string') {
            // Check for TweakDB ID patterns
            if (isTweakDBReference(value)) {
                if (dependencies.indexOf(value) === -1) {
                    dependencies.push(value);
                }
            }
        } else if (Array.isArray(value)) {
            for (var i = 0; i < value.length; i++) {
                extractDependenciesFromObject(value[i], dependencies);
            }
        } else if (typeof value === 'object') {
            extractDependenciesFromObject(value, dependencies);
        }
    }
}

function isTweakDBReference(str) {
    if (!str || typeof str !== 'string') {
        return false;
    }
    
    // Skip obvious non-TweakDB strings
    if (str.length < 3 || str.includes(' ') || str.includes('\n') || str.includes('\t')) {
        return false;
    }
    
    // Common TweakDB patterns - made more permissive
    var patterns = [
        /^[A-Z][a-zA-Z0-9_]*\.[A-Za-z0-9_]+/,    // Items.Something, BaseStats.Something
        /^[a-z]+data[A-Z]/,                       // gamedataConstantStatModifier_Record, etc.
        /^[A-Z][a-zA-Z0-9_]*_Record$/,            // SomeType_Record
        /^[A-Z][a-zA-Z]*\.[A-Z]/,                 // Namespace.Item patterns
        /^[a-z]+\.[A-Z]/                          // lowercase.Uppercase patterns
    ];
    
    var matchesPattern = false;
    for (var i = 0; i < patterns.length; i++) {
        if (patterns[i].test(str)) {
            matchesPattern = true;
            break;
        }
    }
    
    if (!matchesPattern) {
        return false;
    }
    
    // Check if it exists in TweakDB
    try {
        return wkit.HasTDBID(str);
    } catch (error) {
        return false;
    }
}

function trackRecordMetadata(recordData, recordPath, state) {
    try {
        var recordType = extractRecordType(recordData);
        if (recordType && recordType !== "Unknown") {
            state.stats.recordTypesFound[recordType] = true;
            
            // In comprehensive mode, find ALL records of this type
            if (COMPREHENSIVE_MODE && !state.processedTypes) {
                state.processedTypes = {};
            }
            
            if (COMPREHENSIVE_MODE && !state.processedTypes[recordType]) {
                state.processedTypes[recordType] = true;
                logger.Info("Discovering all records of type: " + recordType);
                var allRecordsOfType = findAllRecordsOfType(recordType);
                logger.Info("Found " + allRecordsOfType.length + " records of type " + recordType);
                
                for (var i = 0; i < allRecordsOfType.length && i < MAX_RECORDS_PER_TYPE; i++) {
                    var recordId = allRecordsOfType[i];
                    if (!state.processedRecords[recordId] && state.pendingRecords.indexOf(recordId) === -1) {
                        state.pendingRecords.push(recordId);
                    }
                }
            }
        }
        
        // Extract namespace from record path
        var parts = recordPath.split('.');
        if (parts.length > 1) {
            var namespace = parts[0];
            state.stats.namespacesFound[namespace] = true;
            
            // In comprehensive mode, find ALL records in this namespace
            if (COMPREHENSIVE_MODE && !state.processedNamespaces) {
                state.processedNamespaces = {};
            }
            
            if (COMPREHENSIVE_MODE && !state.processedNamespaces[namespace]) {
                state.processedNamespaces[namespace] = true;
                logger.Info("Discovering all records in namespace: " + namespace);
                var allRecordsInNamespace = findAllRecordsInNamespace(namespace);
                logger.Info("Found " + allRecordsInNamespace.length + " records in namespace " + namespace);
                
                for (var i = 0; i < allRecordsInNamespace.length && i < MAX_RECORDS_PER_TYPE; i++) {
                    var recordId = allRecordsInNamespace[i];
                    if (!state.processedRecords[recordId] && state.pendingRecords.indexOf(recordId) === -1) {
                        state.pendingRecords.push(recordId);
                    }
                }
            }
        }
        
    } catch (error) {
        logger.Error("Error tracking metadata: " + error.message);
    }
}

// ===== COMPREHENSIVE DISCOVERY =====
function findAllRecordsOfType(recordType) {
    var records = [];
    try {
        var allRecords = wkit.GetRecords();
        if (allRecords && allRecords.length) {
            for (var i = 0; i < allRecords.length; i++) {
                var recordPath = allRecords[i];
                try {
                    var recordData = getRecordData(recordPath);
                    if (recordData && recordData.Data && recordData.Data.$type === recordType) {
                        records.push(recordPath);
                    }
                } catch (error) {
                    // Skip individual record errors
                    continue;
                }
            }
        }
    } catch (error) {
        logger.Error("Error finding records of type " + recordType + ": " + error.message);
    }
    return records;
}

function findAllRecordsInNamespace(namespace) {
    var records = [];
    try {
        var allRecords = wkit.GetRecords();
        if (allRecords && allRecords.length) {
            for (var i = 0; i < allRecords.length; i++) {
                var recordPath = allRecords[i];
                if (recordPath.indexOf(namespace + '.') === 0) {
                    records.push(recordPath);
                }
            }
        }
    } catch (error) {
        logger.Error("Error finding records in namespace " + namespace + ": " + error.message);
    }
    return records;
}

// ===== YAML EXPORT =====
function exportToYaml(state, outputDir) {
    try {
        // Group records by type
        var recordsByType = {};
        
        for (var recordPath in state.exportedContent) {
            var recordData = state.exportedContent[recordPath];
            var recordType = extractRecordType(recordData);
            
            if (!recordsByType[recordType]) {
                recordsByType[recordType] = [];
            }
            
            recordsByType[recordType].push({
                path: recordPath,
                data: recordData
            });
        }
        
        // Export each type to separate file
        for (var recordType in recordsByType) {
            var records = recordsByType[recordType];
            var yamlContent = createYamlForType(recordType, records);
            var filename = outputDir + "/" + sanitizeFilename(recordType) + ".yaml";
            
            try {
                wkit.SaveToRaw(filename, yamlContent);
                logger.Info("Exported " + records.length + " records to " + filename);
            } catch (error) {
                logger.Error("Error saving " + filename + ": " + error.message);
            }
        }
        
        // Create comprehensive file
        var comprehensiveYaml = createComprehensiveYaml(state, recordsByType);
        var comprehensiveFilename = outputDir + "/" + sanitizeFilename(STARTING_RECORD) + "_complete_dependencies.yaml";
        
        try {
            wkit.SaveToRaw(comprehensiveFilename, comprehensiveYaml);
            logger.Info("Saved comprehensive file: " + comprehensiveFilename);
        } catch (error) {
            logger.Error("Error saving comprehensive file: " + error.message);
        }
        
    } catch (error) {
        logger.Error("Error during YAML export: " + error.message);
    }
}

function extractRecordType(recordData) {
    if (recordData && recordData.Data && recordData.Data.$type) {
        return recordData.Data.$type;
    } else if (recordData && recordData.RootChunk && recordData.RootChunk.$type) {
        return recordData.RootChunk.$type;
    } else if (recordData && recordData.$type) {
        return recordData.$type;
    }
    return "Unknown";
}

function createYamlForType(recordType, records) {
    var yaml = "# " + recordType + " Records\n";
    yaml += "# Total: " + records.length + "\n";
    yaml += "# Generated: " + new Date().toISOString() + "\n\n";
    
    for (var i = 0; i < records.length; i++) {
        var record = records[i];
        yaml += createYamlForRecord(record.path, record.data) + "\n\n";
    }
    
    return yaml;
}

function createYamlForRecord(recordPath, recordData) {
    try {
        var yaml = recordPath + ":\n";
        
        // Debug the structure we're working with
        if (!recordData) {
            return yaml + "  # No record data\n";
        }
        
        var dataSource = null;
        if (recordData.Data) {
            dataSource = recordData.Data;
        } else if (recordData.RootChunk) {
            dataSource = recordData.RootChunk;
        } else {
            dataSource = recordData;
        }
        
        if (!dataSource) {
            return yaml + "  # No data source found\n";
        }
        
        var dataKeys = Object.keys(dataSource);
        if (dataKeys.length === 0) {
            return yaml + "  # Data source is empty\n";
        }
        
        // Add type info
        if (dataSource.$type) {
            yaml += "  $type: " + dataSource.$type + "\n";
        }
        
        // Add all properties
        for (var key in dataSource) {
            if (key === '$type' || !dataSource.hasOwnProperty(key)) {
                continue;
            }
            
            try {
                yaml += "  " + key + ": " + formatYamlValue(dataSource[key], 2) + "\n";
            } catch (keyError) {
                yaml += "  " + key + ": # Error formatting value: " + keyError.message + "\n";
            }
        }
        
        return yaml;
        
    } catch (error) {
        return "# Error creating YAML for " + recordPath + ": " + error.message + "\n";
    }
}

function formatYamlValue(value, indent) {
    var spaces = "";
    for (var i = 0; i < indent; i++) {
        spaces += " ";
    }
    
    if (value === null || value === undefined) {
        return "null";
    } 
    
    // Handle TweakDB-style objects with $type, $storage, $value
    if (typeof value === 'object' && value.$type && value.$value !== undefined) {
        return formatTweakDBValue(value);
    }
    
    // Handle arrays
    if (Array.isArray(value)) {
        if (value.length === 0) {
            return "[]";
        }
        var result = "";
        for (var i = 0; i < value.length; i++) {
            result += "\n" + spaces + "- " + formatYamlValue(value[i], indent + 2);
        }
        return result;
    }
    
    // Handle objects
    if (typeof value === 'object') {
        // Check for special vector/coordinate objects
        if (isSimpleCoordinateObject(value)) {
            return formatInlineObject(value);
        }
        
        var result = "";
        for (var key in value) {
            if (value.hasOwnProperty(key)) {
                result += "\n" + spaces + key + ": " + formatYamlValue(value[key], indent + 2);
            }
        }
        return result;
    }
    
    // Handle primitives
    if (typeof value === 'string') {
        // Empty strings
        if (value === "") {
            return "''";
        }
        // Don't quote simple TweakDB IDs and paths
        if (isSimpleTweakDBValue(value)) {
            return value;
        }
        return "\"" + value.replace(/"/g, '\\"') + "\"";
    }
    
    if (typeof value === 'boolean') {
        return value ? "True" : "False";  // Capitalize like WolvenKit
    }
    
    if (typeof value === 'number') {
        return value.toString();
    }
    
    return value.toString();
}

function formatTweakDBValue(obj) {
    // Extract the actual value from TweakDB wrapper objects
    if (obj.$type && obj.$value !== undefined) {
        switch (obj.$type) {
            case "TweakDBID":
            case "CName":
                return obj.$value;
            case "Bool":
                return obj.$value ? "True" : "False";
            case "Float":
            case "Int32":
            case "Uint32":
                return obj.$value.toString();
            case "String":
                return obj.$value === "" ? "''" : obj.$value;
            default:
                return obj.$value;
        }
    }
    return obj.toString();
}

function isSimpleTweakDBValue(str) {
    // Don't quote simple TweakDB references, numbers, etc.
    return /^[A-Za-z0-9_\.]+$/.test(str) || 
           /^LocKey#\d+$/.test(str) ||
           /^[+-]?\d*\.?\d+$/.test(str);
}

function isSimpleCoordinateObject(obj) {
    // Check if it's a simple coordinate object like {x: 0, y: 0, z: 0}
    var keys = Object.keys(obj);
    return keys.length <= 4 && 
           keys.every(key => /^[xyz]$/i.test(key) || key === 'w') &&
           keys.every(key => typeof obj[key] === 'number');
}

function formatInlineObject(obj) {
    // Format like {x: 0, y: 0, z: 0}
    var parts = [];
    for (var key in obj) {
        if (obj.hasOwnProperty(key)) {
            parts.push(key + ": " + obj[key]);
        }
    }
    return "{" + parts.join(", ") + "}";
}

function createComprehensiveYaml(state, recordsByType) {
    var yaml = "# TweakDB Recursive Export starting from: " + STARTING_RECORD + "\n";
    yaml += "# Generated: " + new Date().toISOString() + "\n";
    yaml += "# Total records: " + state.stats.totalRecordsExported + "\n";
    yaml += "# Record types: " + Object.keys(state.stats.recordTypesFound).length + "\n";
    yaml += "# Namespaces: " + Object.keys(state.stats.namespacesFound).length + "\n\n";
    
    var sortedTypes = Object.keys(recordsByType).sort();
    for (var i = 0; i < sortedTypes.length; i++) {
        var recordType = sortedTypes[i];
        var records = recordsByType[recordType];
        yaml += "# ===== " + recordType + " Records (" + records.length + ") =====\n\n";
        
        for (var j = 0; j < records.length; j++) {
            var record = records[j];
            yaml += createYamlForRecord(record.path, record.data) + "\n\n";
        }
    }
    
    return yaml;
}

// ===== SUMMARY GENERATION =====
function generateSummary(state, outputDir) {
    var endTime = Date.now();
    var duration = Math.round((endTime - state.stats.startTime) / 1000);
    
    logger.Info("=== Export Summary ===");
    logger.Info("Starting record: " + STARTING_RECORD);
    logger.Info("Total records exported: " + state.stats.totalRecordsExported);
    logger.Info("Record types found: " + Object.keys(state.stats.recordTypesFound).length);
    logger.Info("Namespaces found: " + Object.keys(state.stats.namespacesFound).length);
    logger.Info("Duration: " + duration + " seconds");
    
    // Create summary content
    var summaryContent = "TweakDB Recursive Export Summary\n";
    summaryContent += "Generated: " + new Date().toISOString() + "\n";
    summaryContent += "Starting Record: " + STARTING_RECORD + "\n";
    summaryContent += "Duration: " + duration + " seconds\n\n";
    summaryContent += "Statistics:\n";
    summaryContent += "- Total records exported: " + state.stats.totalRecordsExported + "\n";
    summaryContent += "- Record types found: " + Object.keys(state.stats.recordTypesFound).length + "\n";
    summaryContent += "- Namespaces found: " + Object.keys(state.stats.namespacesFound).length + "\n\n";
    summaryContent += "Record Types:\n";
    
    var recordTypes = Object.keys(state.stats.recordTypesFound).sort();
    for (var i = 0; i < recordTypes.length; i++) {
        summaryContent += "- " + recordTypes[i] + "\n";
    }
    
    summaryContent += "\nNamespaces:\n";
    var namespaces = Object.keys(state.stats.namespacesFound).sort();
    for (var i = 0; i < namespaces.length; i++) {
        summaryContent += "- " + namespaces[i] + "\n";
    }
    
    try {
        var summaryFilename = outputDir + "/export_summary.txt";
        wkit.SaveToRaw(summaryFilename, summaryContent);
        logger.Info("Summary saved to: " + summaryFilename);
    } catch (error) {
        logger.Error("Could not write summary: " + error.message);
    }
    
    // Show completion message
    var message = "Recursive Export Complete!\n\n" +
                   "Starting: " + STARTING_RECORD + "\n" +
                   "Records exported: " + state.stats.totalRecordsExported + "\n" +
                   "Types found: " + Object.keys(state.stats.recordTypesFound).length + "\n" +
                   "Namespaces: " + Object.keys(state.stats.namespacesFound).length + "\n" +
                   "Duration: " + duration + "s\n\n" +
                   "Files saved to raw folder:\n" + outputDir;
    
    wkit.ShowMessageBox(message, "Export Complete", 0, 0);
}

function sanitizeFilename(filename) {
    return filename.replace(/[<>:"/\\|?*]/g, '_').replace(/\s+/g, '_');
}

// Start the export
main(); 
