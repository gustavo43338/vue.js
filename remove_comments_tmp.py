from pathlib import Path
import re

path = Path(r"c:\Users\gusta\proyectovuejs\src\App.vue")
text = path.read_text(encoding="utf-8")
start = text.find("<script setup>")
end = text.find("</script>", start)
if start == -1 or end == -1:
    raise SystemExit("script section not found")
script = text[start+len("<script setup>"):end]

out = []
i = 0
state = 'normal'
quote = None
while i < len(script):
    c = script[i]
    if state == 'normal':
        if c in '"`\'':
            quote = c
            state = 'string'
            out.append(c)
            i += 1
        elif c == '/' and i + 1 < len(script) and script[i + 1] == '/':
            i += 2
            while i < len(script) and script[i] != '\n':
                i += 1
        elif c == '/' and i + 1 < len(script) and script[i + 1] == '*':
            i += 2
            while i + 1 < len(script) and not (script[i] == '*' and script[i + 1] == '/'):
                i += 1
            i += 2
        else:
            out.append(c)
            i += 1
    else:
        out.append(c)
        if c == '\\':
            if i + 1 < len(script):
                out.append(script[i + 1])
                i += 2
                continue
        elif c == quote:
            state = 'normal'
        i += 1
script_clean = ''.join(out)

template_start = text.find('<template>')
template_end = text.find('</template>', template_start)
style_start = text.find('<style')
style_end = text.rfind('</style>')
if template_start == -1 or template_end == -1 or style_start == -1 or style_end == -1:
    raise SystemExit('template/style section not found')

template = text[template_start:template_end + len('</template>')]
style = text[style_start:style_end + len('</style>')]

template_clean = re.sub(r'<!--.*?-->', '', template, flags=re.S)
style_clean = re.sub(r'/\*.*?\*/', '', style, flags=re.S)

full = text[:start + len('<script setup>')] + script_clean + text[end:]
full = full.replace(template, template_clean)
full = full.replace(style, style_clean)
path.write_text(full, encoding='utf-8')
print('comments removed')
