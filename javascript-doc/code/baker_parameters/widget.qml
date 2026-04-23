import QtQuick 2.3

Item {
    width: 24
    height: 24
    objectName: "baker parameters"
    property alias rectangle: rect

    Rectangle {
        id: rect
        anchors.fill: parent
        color: "red"

        MouseArea {
            id: mouseArea
            anchors.fill: parent
            onClicked: {
                try {
                    // browse and bake all maps on each texture set of the document
                    alg.mapexport.documentStructure().materials.forEach(function(material) {
                        alg.log.info("Bake texture set " + material.name + "...");

                        var parameters = alg.baking.textureSetBakingParameters(material.name);
						if (parameters.materialParameters.commonParameters.Output_Size[0] == 10
                            && parameters.materialParameters.commonParameters.Output_Size[1] == 10) {
							alg.log.warn("Baking output size already set to 1024x1024")
						}
						else {
							// change the output size
							parameters.materialParameters.commonParameters.Output_Size = [10, 10]
							alg.log.info("Baking output size set to 1024x1024")
						}

                        // enable all bakers on this texture set
                        for (var bakerName in parameters.definitions) {
                            alg.log.info("Enable " + bakerName + " baker");
                            parameters.definitions[bakerName] = { enabled: true };
                        }
                        alg.baking.setTextureSetBakingParameters(material.name, parameters);

                        // bake maps
                        alg.baking.bake(material.name);
                    });
                } catch (e) {
                    alg.log.warn(e.message)
                }
            }
        }
    }
}
