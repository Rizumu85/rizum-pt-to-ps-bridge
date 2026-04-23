import QtQml 2.1
import QtQuick 2.7
import QtWebSockets 1.0
import Painter 1.0

PainterPlugin {
  Component.onCompleted: {
    // Open the browser sample page, able to communicate with Substance 3D Painter
    // If this doesn't automatically open a web page, you can open this file yourself in your browser
    Qt.openUrlExternally('browser_websocket_example.html');
  }

  // Declare a WebSocket server listening on the port 12345
  // The WebSocket url will be ws://localhost:12345/ or ws://[MY_IP]:12345/
  WebSocketServer {
    listen: true
    port: 12345

    onClientConnected: {
      alg.log.info("New client connected");
      // The clientConnected signal is called with a webSocket object in parameter that represents
      // the newly created connection between the server and the client.
      // When we receive a message from a connected client, display it, then send back a message.
      webSocket.onTextMessageReceived.connect(function(message) {
        var date = (new Date()).toLocaleTimeString();

        alg.log.info("Message received at %1: %2".arg(date).arg(message));

        webSocket.sendTextMessage(( // Send HTML content to be displayed in the browser
          "<h1>Hello!</h3>" +
          "<p>Your are connected to Substance 3D Painter via a WebSocket</p>" +
          "<ul>" +
          "  <li>Time: %1</li>" +
          "  <li>Substance 3D Painter version: %2</li>" +
          "  <li>Scripting API version: %3</li>" +
          "</ul>"
        ).arg(date).arg(alg.version.painter).arg(alg.version.api));
      });
    }
  }
}
