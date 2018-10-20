let huddleButton = document.querySelector("#huddle-button");
let recordingStatus = document.querySelector("#rec-status");
let speechRecognition = new webkitSpeechRecognition();
speechRecognition.lang = "en-US";
speechRecognition.continuous = true;
speechRecognition.interimResults = false;

huddleButton.addEventListener("click", () => {
  if (huddleButton.classList.contains("rec-active")) {
    stopRecording();
    speechRecognition.stop();
  } else {
    startRecording();
    speechRecognition.start();
    speechRecognition.onend = () => {
      console.log("Restarting");
      speechRecognition.start();
    }
    speechRecognition.onresult = (event) => {
      var speech = event.results[event.results.length-1][0].transcript;
      console.log(speech);
    }
  }
});

function stopRecording() {
  huddleButton.classList.replace("rec-active", "rec-inactive");
  huddleButton.classList.replace("btn-success", "btn-danger");
  huddleButton.innerHTML = "Start Huddle Session";
  recordingStatus.innerHTML = "";
}

function startRecording() {
  huddleButton.classList.replace("rec-inactive", "rec-active");
  huddleButton.classList.replace("btn-danger", "btn-success");
  huddleButton.innerHTML = "Stop Huddle Session";
  recordingStatus.innerHTML = "Recording..";
}
