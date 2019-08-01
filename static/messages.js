async function getMessages() {
  var newMessages = await fetch("/MessagesJSON");
  var messagesjson=await newMessages.json();
  var messagesstring = "";
  for(var i=0; i<messagesjson.length; i++) {
    messagesstring += messagesjson[i].timestamp + " | <b>" +
                      messagesjson[i].sender+ "</b>: " +
                      messagesjson[i].message + "<br>";
  }
  document.getElementById("forLoop").innerHTML = messagesstring;
}

function init() {
  setInterval(getMessages, 5*1000);
}

init();
