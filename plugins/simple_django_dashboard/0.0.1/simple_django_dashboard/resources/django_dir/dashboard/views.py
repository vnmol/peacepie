from django.http import HttpResponse

from . import html_addons, zmq_client


PAGE_SIZE = 5


async def root(request):
    param_level = request.GET.get('level')
    param_recipient = request.GET.get('recipient')
    param_id = request.GET.get('id')
    body = {'page_size': PAGE_SIZE, 'level': param_level, 'id': param_id}
    msg = {'command': 'get_members', 'body': body, 'recipient': param_recipient}
    ans = zmq_client.client.send_request(msg)
    head = f'<head>\n<meta charset="UTF-8">\n<style>\n{html_addons.entity_style}\n</style>\n</head>\n\n'
    text = f'<!DOCTYPE html>\n<html>\n{head}<body>\n\n'
    body = ans.get('body')
    if body.get('_back'):
        text += back(body)
    text += members(body)
    if body.get('nav'):
        text += nav(body)
    if body.get('level') == 'actor':
        text += comm(body)
    text += '<script>\n'
    text += html_addons.script_common
    if body.get('level') == 'actor':
        text += script_command('localhost', request.META['SERVER_PORT'])
    text += '</script>\n</body>\n</html>'
    return HttpResponse(text)


def back(body):
    bck = body.get('_back')
    res = f'<button class="entity" id="{bck.get("id")}"'
    res += f' data-next_level="{bck.get("next_level")}" data-recipient="{bck.get("recipient")}"'
    res += f'>..</button>\n<br><br>\n'
    return res


def members(body):
    res = ''
    for member in body.get('members'):
        clss = 'last_entity' if not member.get('next_level') else 'entity'
        res += f'<button class="{clss}" id="{member.get("id")}"'
        res += f' data-next_level="{member.get("next_level")}" data-recipient="{member.get("recipient")}"'
        res += f'>{member.get("id")}</button>\n'
    return res


def nav(body):
    nv = body.get('nav')
    count = nv.get('count')
    page = nv.get('page')
    res = '<br><br><br><div class="container">\n'
    if page > 0:
        res += f'<button class="entity nav" id="_page_{page - 1}"'
        res += f' data-next_level="{nv.get("next_level")}" data-recipient="{nv.get("recipient")}"'
        res += '><</button>\n'
    res += f'<button id="page" class="page">{page + 1}</button>\n'
    if page < count - 1:
        res += f'<button class="entity nav" id="_page_{page + 1}"'
        res += f' data-next_level="{nv.get("next_level")}" data-recipient="{nv.get("recipient")}"'
        res += '>></button>\n'
    res += '</div>\n'
    return res


def comm(body):
    recipient = body.get('members')[0].get('id')
    res = html_addons.script_command_begin
    res += f'  <input type="text" id="recipient" name="recipient" value="{recipient}">\n'
    res += html_addons.script_command_end
    return res

def script_command(host, port):
    res = f'webSocket = new WebSocket("ws://{host}:{port}/ws");'
    res += html_addons.script_websocket
    return res
