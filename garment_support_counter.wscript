// Count meshes with garment support, ignoring shadow meshes
// @author MisterChedda
// @version 1.3

import * as Logger from 'Logger.wscript';
import * as TypeHelper from 'TypeHelper.wscript';

let totalMeshes = 0;
let meshesWithGarmentSupport = 0;

for (let filename of wkit.GetProjectFiles('archive')) {
    if (filename.split('.').pop() === "mesh" && !filename.toLowerCase().includes("shadow")) {
        totalMeshes++;
        try {
            const fileContent = wkit.LoadGameFileFromProject(filename, 'json');
            const mesh = TypeHelper.JsonParse(fileContent);
            
            if (mesh && mesh.Data && mesh.Data.RootChunk && mesh.Data.RootChunk.parameters) {
                const hasGarmentSupport = mesh.Data.RootChunk.parameters.some(param => 
                    param.Data && param.Data.$type === "meshMeshParamGarmentSupport"
                );
                
                if (hasGarmentSupport) {
                    meshesWithGarmentSupport++;
                }
            }
        } catch (err) {
            Logger.Error(`Error processing ${filename}: ${err.message}`);
        }
    }
}

Logger.Info(`Total number of non-shadow mesh files: ${totalMeshes}`);
Logger.Info(`Number of non-shadow meshes with garment support: ${meshesWithGarmentSupport}`);
Logger.Info(`Percentage of non-shadow meshes with garment support: ${((meshesWithGarmentSupport / totalMeshes) * 100).toFixed(2)}%`);
