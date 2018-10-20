paper.install(window);
window.onload = function() {
  var canvas = $("#huddle-canvas")[0];
  var pinCanvas = $("#pin-canvas");
  const context = canvas.getContext('2d');

  // Paper.js
  paper.setup("huddle-canvas");
  var tool = new Tool();
  var path;

  tool.onMouseDown = function(event) {
    path = new Path();
    path.strokeColor = "red";
    path.strokeWidth = 3;
    path.add(event.point);
  }

  tool.onMouseDrag = function(event) {
    path.add(event.point);
  }

  pinCanvas.on("click", () => {
    canvas.toBlob(blob => {
      pinImageToTrello(blob);
    });
    project.clear();
  });

  async function pinImageToTrello(blob) {
    const KEY = "9699a11bcd760a9dd78e59338314e870";
    const TOKEN = "01aeff8a98124ef0e63130c2c44a34284be6df1f604c427e17b603a3ae78d6b1";
    let response = await fetch("https://api.trello.com/1/cards?name=" + "Drawing" + "&idList=" + "5bcba3b2a8e0c8373c67eea1" + "&key=" + KEY + "&token=" + TOKEN, {
      method: "POST",
    });
    response.json().then(card => {
      createAndSendForm(blob, card.id);
    });
  }

  const createAndSendForm = function(file, cardId) {
    var formData = new FormData();
    formData.append("key", "9699a11bcd760a9dd78e59338314e870");
    formData.append("token", "01aeff8a98124ef0e63130c2c44a34284be6df1f604c427e17b603a3ae78d6b1");
    formData.append("file", file);
    formData.append("mimeType", "image/jpeg");
    formData.append("name", "My Awesome File");
    var request = createRequest(cardId);
    request.send(formData);
  }

  const createRequest = function(cardId) {
    var request = new XMLHttpRequest();
    request.onreadystatechange = function() {
      // When we have a response back from the server we want to share it!
      // https://developer.mozilla.org/en-US/docs/Web/API/XMLHttpRequest/response
      if (request.readyState === 4) {
        console.log(`Successfully uploaded at: ${request.response.date}`);
      }
    }
    request.open("POST", `https://api.trello.com/1/cards/${cardId}/attachments/`);
    return request;
  }
}
