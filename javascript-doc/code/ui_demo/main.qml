import QtQuick 2.2
import Painter 1.0

PainterPlugin {

		Component.onCompleted: {
				// create toolbar buttons
				var t = alg.ui.addToolBarWidget("dock.qml");
				t.rectangle.color = "blue"
				t = alg.ui.addToolBarWidget("dock.qml");
				t.rectangle.color = "green"
				t = alg.ui.addToolBarWidget("dock.qml");
				t.rectangle.color = "yellow"
				t = alg.ui.addToolBarWidget("dock.qml");
				t.rectangle.color = "purple"
				// create a dock widget
				alg.ui.addDockWidget("dock.qml");
		}

}
