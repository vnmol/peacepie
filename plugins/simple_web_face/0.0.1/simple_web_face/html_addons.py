import logging

entity_style = '''.entity {
  width: 60%;
  background-color: #EC5800;
  border: none;
  color: white;
  padding: 20px;
  text-align: center;
  text-decoration: none;
  display: block;
  font-size: 40px;
  margin-left: auto;
  margin-right: auto;
  margin-top: 20px;
  cursor: pointer;
  border-radius: 8px;
}
.entity.nav {
  width: 60px;
  display: inline-block;
}
.ask_send {
  width: 20%;
  display: inline-block;
  background-color: #EC5800;
  border: none;
  color: white;
  padding: 20px;
  text-align: center;
  text-decoration: none;
  font-size: 40px;
  cursor: pointer;
  border-radius: 8px;
  margin-right: 20px;
}
.container {
  text-align: center;
}
.input_container {
  width: 60%;
  margin-left: auto;
  margin-right: auto;
  margin-bottom: 20px;
}
.page {
  width: 60px;
  background-color: #B92500;
  border: none;
  color: white;
  padding: 20px;
  text-align: center;
  text-decoration: none;
  display: inline-block;
  font-size: 40px;
  margin-left: auto;
  margin-right: auto;
  margin-top: 20px;
  cursor: pointer;
  border-radius: 8px;
}
.last_entity {
  width: 60%;
  background-color: #B92500;
  border: none;
  color: white;
  padding: 20px;
  text-align: center;
  text-decoration: none;
  display: block;
  font-size: 40px;
  margin-left: auto;
  margin-right: auto;
  margin-top: 20px;
  cursor: pointer;
  border-radius: 8px;
}
label {
  display: block;
  font-size: 40px;
}
input, textarea {
  width: 100%;
  padding: 8px;
  box-sizing: border-box;
  text-align: left;
  font-size: 40px;
}
'''

script_common = '''
\n
  function handleClick(event) {
    level = event.target.dataset.next_level
    recipient = event.target.dataset.recipient
    ref = '/?level=' + level + '&recipient=' + recipient + '&id=' + event.target.id;
    window.location.href = ref
  }

  document.querySelectorAll('.entity').forEach(button => {
    button.addEventListener('click', handleClick);
  });
'''


script_websocket = '''
    webSocket.onmessage = (event) => {
        document.getElementById("answer").value = event.data;
    };
    function send(id) {
      document.getElementById("answer").value = "";
      var body_val = document.getElementById("body").value;
      try {
        body_val = JSON.parse(body_val);
      } catch(e) {
      }
      var recipient_val = document.getElementById("recipient").value;
      try {
        recipient_val = JSON.parse(recipient_val);
      } catch(e) {
      }
      msg = {
        type: id,
        command: document.getElementById("command").value,
        body: body_val,
        timeout: document.getElementById("timeout").value,
        recipient: recipient_val,
      };
      webSocket.send(JSON.stringify(msg));
    };
'''


script_command_begin = '''
    <br><br><br>
    <div class="input_container">
      <label for="command">Команда</label>
      <input type="text" id="command" name="command">
    </div>
    <div class="input_container">
      <label for="body">Тело</label>
      <textarea id="body" name="body" rows="4"></textarea>
    </div>
    <div class="input_container">
      <label for="timeout">Таймаут</label>
      <input type="text" id="timeout" name="timeout" value="10">
    </div>
    <div class="input_container">
      <label for="recipient">Получатель</label>
'''


script_command_end = '''
    </div>
    <br><br><br><div class="container">
    <button class="ask_send" id="ask" onclick="send(this.id)">ASK</button>
    <button class="ask_send" id="send" onclick="send(this.id)">SEND</button>
    </div>
    <br><br><br><div class="input_container">
      <label for="answer">Ответ сервера</label>
      <textarea id="answer" name="answer" rows="4"></textarea>
    </div>
'''


def template_format(template, fields):
    res = template
    for key, value in fields.items():
        try:
            res = res.replace('{{' + key + '}}', value)
        except Exception as e:
            logging.exception(e)
    return res
