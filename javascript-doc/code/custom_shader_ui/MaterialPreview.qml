import QtQuick 2.7
import QtQuick.Controls 2.0
import QtQuick.Layouts 1.3
import AlgWidgets 2.0

ColumnLayout {
  id: root
  spacing: 0
  property alias text: label.text
  property var material: null
  property bool selected: false
  signal clicked()

  Component.onCompleted: {
    button.clicked.connect(clicked)
  }

  Button {
    id: button

    property var previewOpacity: selected?
      1 :
      pressed ? 0.2 : 0.6

    background: Rectangle {
      anchors.fill: button
      implicitWidth: 50
      implicitHeight: 50
      color: "transparent"
    }

    Image {
      mipmap: true
      cache: false
      anchors.fill: parent
      fillMode: Image.PreserveAspectFit
      opacity: button.previewOpacity
      visible: root.material && root.material.value
      source: "image://resources/" + ((root.material && root.material.value)?
        root.material.value : "")
    }

    Rectangle {
      anchors.fill: parent
      opacity: button.previewOpacity
      visible: !(root.material && root.material.value)
      radius: width*0.5
      color : "#111"
    }

    Rectangle {
      anchors.fill: parent
      visible: selected
      border.color: "#000"
      border.width: 1
      color: "transparent"
      opacity: 0.5
    }
  }
  AlgLabel {
    id: label
    Layout.alignment: Qt.AlignHCenter
  }
}
