"""Metadata retrieval only: no claim of automated scientific extraction."""
import httpx
async def search(query):
    if not 3<=len(query.strip())<=300: raise ValueError('Saisissez entre 3 et 300 caractères.')
    async with httpx.AsyncClient(timeout=20,headers={'User-Agent':'MateriaResearchPrototype/0.1'}) as client:
        response=await client.get('https://api.crossref.org/works',params={'query.bibliographic':query,'rows':8,'select':'DOI,title,author,published,URL'})
        response.raise_for_status()
    return [dict(title=(item.get('title') or ['Sans titre'])[0],doi=item['DOI'],url='https://doi.org/'+item['DOI'],year=(item.get('published',{}).get('date-parts') or [['—']])[0][0]) for item in response.json()['message']['items']]
