import QtQuick 2.2
import Painter 1.0

PainterPlugin {

    Component.onCompleted: {
        // create a toolbar widget
        alg.ui.addToolBarWidget("widget.qml");
    }

}
