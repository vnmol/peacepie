import logging


script_common = '''
\n
  function handleClick(event) {
    level = event.target.dataset.next_level
    recipient = event.target.dataset.recipient
    ref = '/actors/?level=' + level + '&recipient=' + recipient + '&id=' + event.target.id;
    window.location.href = ref
  }

  document.querySelectorAll('.entity').forEach(button => {
    button.addEventListener('click', handleClick);
  });
'''


script_command_begin = '''
    <br>
    <div class="input_container">
      <label for="command">Команда</label>
      <input type="text" id="command" name="command">
    </div>
    <div class="input_container">
      <label for="body">Тело</label>
      <textarea id="body" name="body" rows="2"></textarea>
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
    <br><div class="container">
    <button class="ask_send" id="ask" onclick="send(this.id)">ASK</button>
    <button class="ask_send" id="send" onclick="send(this.id)">SEND</button>
    </div>
    <br><div class="input_container">
      <label for="answer">Ответ сервера</label>
      <textarea id="answer" name="answer" rows="2"></textarea>
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
