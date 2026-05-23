import json, random, collections
random.seed(42)

data=json.load(open('app/nlu/dataset/panic_data_bio.json',encoding='utf8'))
langs=collections.Counter([e['language'] for e in data])
samples={}
for L in sorted(langs.keys()):
    items=[e for e in data if e['language']==L]
    samples[L]=[]
    for ex in random.sample(items, min(10,len(items))):
        samples[L].append({
            'id': ex['id'],
            'text': ex['text'],
            'tokens': ex['tokens'],
            'bio_tags': ex['bio_tags']
        })
open('app/nlu/dataset/samples_per_language.json','w',encoding='utf8').write(json.dumps(samples,ensure_ascii=False,indent=2))
print('Wrote samples to app/nlu/dataset/samples_per_language.json')
