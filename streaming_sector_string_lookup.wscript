// Search for string in streaming sectors
// @author MisterChedda
// @version 1.1
import * as Logger from 'Logger.wscript';
import * as TypeHelper from 'TypeHelper.wscript';

// The string to search for
const searchString = "put_search_string_here";

// Function to search for the string in a node and its children
function searchInNode(node, results) {
    if (typeof node === 'object' && node !== null) {
        for (let key in node) {
            if (typeof node[key] === 'string' && node[key].includes(searchString)) {
                results.count++;
            }
            if (typeof node[key] === 'object') {
                searchInNode(node[key], results);
            }
        }
    }
}

// Process each streaming sector file
for (let filename of wkit.GetProjectFiles('archive')) {
    if (filename.endsWith('.streamingsector')) {
        try {
            const fileContent = wkit.LoadGameFileFromProject(filename, 'json');
            const sector = TypeHelper.JsonParse(fileContent);
            
            let results = { count: 0 };
            
            if (sector && sector.Data && sector.Data.RootChunk) {
                searchInNode(sector.Data.RootChunk, results);
            }
            
            if (results.count > 0) {
                Logger.Info(`${filename}: ${results.count} instance(s)`);
            }
        } catch (err) {
            Logger.Error(`Error processing ${filename}: ${err.message}`);
        }
    }
}

Logger.Info('Search completed.');
