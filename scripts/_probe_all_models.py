"""
Test free-tier models with the correct model IDs that actually work on free plans.
These providers accept the "free" placeholder key only if OmniRoute has a shared pool,
OR these are the models known to work on genuinely keyless/free-tier endpoints.
"""
import urllib.request, json, time, sys, os
os.environ['PYTHONUTF8'] = '1'

OMNIROUTE_URL = 'http://localhost:20128'
KEY = 'sk-2daf4dd6d1e45047-53255c-89ec5ddf'

def call(model, timeout=20):
    body = json.dumps({
        'model': model,
        'messages': [{'role': 'user', 'content': 'Reply with just: OK'}],
        'max_tokens': 8,
        'stream': False
    }).encode()
    req = urllib.request.Request(
        OMNIROUTE_URL + '/v1/chat/completions', data=body,
        headers={
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + KEY,
            'Accept': 'application/json'
        }, method='POST')
    t0 = time.time()
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        resp = json.loads(r.read())
        txt = resp['choices'][0]['message']['content']
        txt_safe = txt.encode('ascii', 'replace').decode()[:35]
        return 'OK', round(time.time() - t0, 1), txt_safe
    except urllib.error.HTTPError as e:
        b = e.read().decode(errors='replace')
        # Extract short error message
        try:
            err = json.loads(b)
            msg = err.get('error', {}).get('message', b)[:80]
        except Exception:
            msg = b[:80]
        return 'HTTP' + str(e.code), round(time.time() - t0, 1), msg
    except Exception as ex:
        return type(ex).__name__, round(time.time() - t0, 1), str(ex)[:60]

# Free models to test — using known free-tier model IDs
tests = [
    # Already confirmed working
    ('agy/gemini-2.5-flash',                              'agy'),
    ('agy/claude-sonnet-4-6',                             'agy'),
    ('antigravity/claude-sonnet-4-6',                     'antigravity'),
    # Free-tier with real free keys (some may work via OmniRoute shared pool)
    ('openrouter/qwen/qwen3-8b:free',                     'openrouter'),
    ('openrouter/meta-llama/llama-3.2-3b-instruct:free',  'openrouter'),
    ('openrouter/google/gemma-3-12b-it:free',             'openrouter'),
    ('sambanova/Meta-Llama-3.1-8B-Instruct',              'sambanova'),
    ('sambanova/Llama-3.2-3B-Instruct',                   'sambanova'),
    ('cerebras/llama3.1-8b',                              'cerebras'),
    ('cerebras/llama-3.3-70b',                            'cerebras'),
    ('groq/llama-3.1-8b-instant',                         'groq'),
    ('groq/gemma2-9b-it',                                 'groq'),
    ('chutes/deepseek-ai/DeepSeek-V3-0324',               'chutes'),
    ('chutes/Qwen/Qwen3-30B-A3B',                         'chutes'),
    ('deepseek/deepseek-chat',                            'deepseek'),
    ('mistral/mistral-small-latest',                      'mistral'),
    ('mistral/open-mistral-nemo',                         'mistral'),
    ('cohere/command-r-plus-08-2024',                     'cohere'),
    ('together/meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo', 'together'),
    ('scaleway/llama-3.3-70b-instruct',                   'scaleway'),
    ('novita/meta-llama/llama-3.1-8b-instruct',           'novita'),
    ('nebius/meta-llama/Meta-Llama-3.1-8B-Instruct',      'nebius'),
    ('deepinfra/meta-llama/Meta-Llama-3.1-8B-Instruct',   'deepinfra'),
    ('hyperbolic/meta-llama/Llama-3.2-3B-Instruct',       'hyperbolic'),
    ('fireworks/accounts/fireworks/models/llama-v3p1-8b-instruct', 'fireworks'),
    ('siliconflow/Qwen/Qwen2.5-7B-Instruct',              'siliconflow'),
    ('friendliai/meta-llama-3-8b-instruct',               'friendliai'),
    ('huggingface/HuggingFaceH4/zephyr-7b-beta',          'huggingface'),
    ('kilocode/claude-sonnet-4-5',                        'kilocode'),
    ('kimi-coding/moonshot-v1-8k',                        'kimi'),
    ('nvidia/z-ai/glm-5.2',                               'nvidia'),
]

header = '{:<55} {:<12} {:>6}  {}'.format('Model', 'Status', 'Time', 'Response')
print(header)
print('-' * 110)

working = []
failed = []
for model, group in tests:
    status, elapsed, resp = call(model)
    flag = 'OK ' if status == 'OK' else '   '
    line = '{}{:<53} {:<12} {:>5.1f}s  {}'.format(flag, model, status, elapsed, resp[:45])
    print(line)
    sys.stdout.flush()
    if status == 'OK':
        working.append((model, group))
    else:
        failed.append((model, status, resp[:50]))
    time.sleep(0.3)

print()
print('=' * 60)
print('WORKING: {}/{}'.format(len(working), len(tests)))
for m, g in working:
    print('  + [{:12}] {}'.format(g, m))
print()
print('NEED REAL API KEY ({} providers):'.format(len(failed)))
seen = set()
for m, s, r in failed:
    provider = m.split('/')[0]
    if provider not in seen:
        seen.add(provider)
        print('  - {} ({})'.format(provider, s))
