// Count meshes with garment support, categorized by path
// @author MisterChedda
// @version 1.5
import * as Logger from 'Logger.wscript';
import * as TypeHelper from 'TypeHelper.wscript';

let totalMeshes = 0;
let meshesWithGarmentSupport = 0;
let ep1Meshes = 0;
let ep1MeshesWithGarmentSupport = 0;
let baseMeshes = 0;
let baseMeshesWithGarmentSupport = 0;

function checkMesh(filename) {
    try {
        const fileContent = wkit.LoadGameFileFromProject(filename, 'json');
        const mesh = TypeHelper.JsonParse(fileContent);
        
        if (mesh && mesh.Data && mesh.Data.RootChunk && mesh.Data.RootChunk.parameters) {
            return mesh.Data.RootChunk.parameters.some(param => 
                param.Data && param.Data.$type === "meshMeshParamGarmentSupport"
            );
        }
    } catch (err) {
        Logger.Error(`Error processing ${filename}: ${err.message}`);
    }
    return false;
}

for (let filename of wkit.GetProjectFiles('archive')) {
    if (filename.split('.').pop() === "mesh" && !filename.toLowerCase().includes("shadow")) {
        totalMeshes++;
        const hasGarmentSupport = checkMesh(filename);
        if (hasGarmentSupport) meshesWithGarmentSupport++;

        if (filename.startsWith("ep1")) {
            ep1Meshes++;
            if (hasGarmentSupport) ep1MeshesWithGarmentSupport++;
        } else if (filename.startsWith("base")) {
            baseMeshes++;
            if (hasGarmentSupport) baseMeshesWithGarmentSupport++;
        }
    }
}

function logStats(total, withGarment, label) {
    Logger.Info(`${label} mesh files: ${total}`);
    Logger.Info(`${label} meshes with garment support: ${withGarment}`);
    Logger.Info(`Percentage of ${label.toLowerCase()} meshes with garment support: ${((withGarment / total) * 100).toFixed(2)}%`);
    Logger.Info('--------------------');
}

logStats(totalMeshes, meshesWithGarmentSupport, "Total non-shadow");
logStats(ep1Meshes, ep1MeshesWithGarmentSupport, "EP1");
logStats(baseMeshes, baseMeshesWithGarmentSupport, "Base");

// Calculate percentage of EP1 vs Base meshes
const ep1Percentage = (ep1Meshes / totalMeshes) * 100;
const basePercentage = (baseMeshes / totalMeshes) * 100;

Logger.Info('EP1 vs Base Comparison:');
Logger.Info(`EP1 meshes: ${ep1Percentage.toFixed(2)}% of total`);
Logger.Info(`Base meshes: ${basePercentage.toFixed(2)}% of total`);

// Calculate percentage of garment support in EP1 vs Base
const ep1GarmentPercentage = (ep1MeshesWithGarmentSupport / meshesWithGarmentSupport) * 100;
const baseGarmentPercentage = (baseMeshesWithGarmentSupport / meshesWithGarmentSupport) * 100;

Logger.Info('Garment Support Distribution:');
Logger.Info(`EP1 meshes: ${ep1GarmentPercentage.toFixed(2)}% of all garment-supported meshes`);
Logger.Info(`Base meshes: ${baseGarmentPercentage.toFixed(2)}% of all garment-supported meshes`);
