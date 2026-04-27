/*************************************************************************
* ADOBE CONFIDENTIAL
*
* Copyright 2016 Adobe
* All Rights Reserved.
*
* NOTICE:  All information contained herein is, and remains
* the property of Adobe and its suppliers, if any. The intellectual
* and technical concepts contained herein are proprietary to Adobe
* and its suppliers and are protected by all applicable intellectual
* property laws, including trade secret and copyright laws.
* Dissemination of this information or reproduction of this material
* is strictly forbidden unless prior written permission is obtained
* from Adobe.
*************************************************************************/

// Connect a shader parameter to the property of a QML component
// @param qmlComponent QML component
// @param propertyKey QML component key to bind
// @param shaderParameter Shader parameter object
function connectPropertyToShaderParameter(qmlComponent, propertyKey, shaderParameter) {
  // Set QML property to the current parameter value
  qmlComponent[propertyKey] = shaderParameter.value;

  // When the QML property has changed, update shader parameter data
  qmlComponent[propertyKey+"Changed"].connect(function() {
    shaderParameter.value = qmlComponent[propertyKey];
  });

  // When the shader parameter data has changed, update the QML property
  shaderParameter.valueChanged.connect(function() {
    qmlComponent[propertyKey] = shaderParameter.value;
  });
}
