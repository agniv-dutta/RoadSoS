import json, random, collections
random.seed(42)

data=json.load(open('app/nlu/dataset/panic_data_bio.json',encoding='utf8'))
intents=collections.Counter()
langs=collections.Counter()
for ex in data:
    intents[ex['intent']]+=1
    langs[ex['language']]+=1
print('Overall intents:',dict(intents))
print('Overall langs:',dict(langs))
# per split counts
for split in ['train','val','test']:
    sdata=json.load(open(f'app/nlu/dataset/{split}.json',encoding='utf8'))
    print(split,'intents',dict(collections.Counter([e['intent'] for e in sdata])))
    print(split,'langs',dict(collections.Counter([e['language'] for e in sdata])))
# samples
for L in sorted(langs.keys()):
    items=[e for e in data if e['language']==L]
    print('---',L,'count',len(items))
    for ex in random.sample(items, min(10,len(items))):
        print(ex['id'], ex['text'])
