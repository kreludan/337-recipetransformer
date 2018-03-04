# -*- coding: utf-8 -*-
"""
@author: Vikram Kohli

Ingredient parser testing; URLs used + issues encountered

https://www.allrecipes.com/recipe/13076/bacon-and-potato-soup/
Issues: no huge ones; used this recipe as a 'starting point' for making the parser

https://www.allrecipes.com/recipe/100506/irish-potato-farls/
Issues: '1/4 cup all-purpose flour, plus extra for dusting' didn't do so great (esp. the clause w/ 'plus')
The word 'cup' is interpreted by NLTK's tagger as an adjective? Same with 'medium' as a noun.
Gonna keep a running global list of these things that can be manually fixed before parsing, at the top of the file.

https://www.allrecipes.com/recipe/79754/lauries-stuffed-peppers/
More manual fixes required... maybe there's a better part-of-speech tagger out there
Forgot to account for details that are included in parentheses; I think they probably belong in the descriptor section
How to deal with words like 'with'? At least for the first try, I'm gonna just append 'with' to both the name and descriptor
Because it seems like that'll be sufficient to tell what's going on

https://www.allrecipes.com/recipe/11116/cream-cheese-sugar-cookies/
First big issue with the parser shows up here... '1 egg yolk' has the parser thinking 'egg' is the measurement.
Probably just best to keep a running list of 'measurement' words, and separate food items from measurements based on that.
This fixed it for this URL; double checked with other recipes and seemed good.

https://www.allrecipes.com/recipe/11901/to-die-for-fettuccini-alfredo/
Small issue; 'ground' isn't picked up as a past-tense verb, but as a noun; adding a fix
Updating 'to taste' to be a measurement worked out OK

https://www.allrecipes.com/recipe/12804/seared-scallops-with-spicy-papaya-sauce/
Labeled as a 'gourmet'/complex recipe, so maybe something weird will happen? (':
Nope. It was getting confused about verb past participles but that was fixed fairly fast

Tool parser testing;

https://www.allrecipes.com/recipe/12804/seared-scallops-with-spicy-papaya-sauce/
Used this one initially; works OK. Came up with a pretty decent list of initial ban words, and the method seems to be OK?

https://www.allrecipes.com/recipe/11901/to-die-for-fettuccini-alfredo/
This one's annoying; the person spelled fettucine two different ways, so the method can't match the two.
Added a method for accounting for typos. Maybe should write a simple inference function that adds intuitive tools necessary?

https://www.allrecipes.com/recipe/11116/cream-cheese-sugar-cookies/

"""

from bs4 import BeautifulSoup
import urllib.request
from nltk import pos_tag, word_tokenize

#   For now, the URL has to be manually changed here
#   Ideally by the end we'll have some walkthrough / user input interface which will be nicer
set_url = "https://www.allrecipes.com/recipe/11116/cream-cheese-sugar-cookies/"

def fetch_page(link):
    with urllib.request.urlopen(link) as url:
        s = url.read()
        soup = BeautifulSoup(s, "lxml")
        
        # Fetch ingredients
        ing_spans = soup.findAll("span", {"class": "recipe-ingred_txt added"})
        ing_strings = [span.text for span in ing_spans]
    
        # Fetch directions
        dir_spans = soup.findAll("span", {"class": "recipe-directions__list--item"})
        dir_strings = [span.text for span in dir_spans]
        
        # Fetch title
        title = soup.find("title").text
        
        return [ing_strings, dir_strings, title]

def deparenthesize(tokenized_phrase):   # stuff in parentheses most often seems like descriptors, so just doing that beforehand
    parenthesized_indices = []
    for i in range(0, len(tokenized_phrase)):
        if tokenized_phrase[i] == '(':
            parenthesized_indices.append(i)
            for j in range(i+1, len(tokenized_phrase)):
                parenthesized_indices.append(j)
                if tokenized_phrase[j] == ')':
                    break
    deparenthesized = [tokenized_phrase[i] for i in range(0, len(tokenized_phrase)) if i not in parenthesized_indices]
    parenthesized = [tokenized_phrase[i] for i in range(0, len(tokenized_phrase)) if i in parenthesized_indices]
    return [deparenthesized, parenthesized]

def parts_fix(tuples):
    #  Keeping a running list of types of measurements; seems like a reasonable way to resolve it
    measurements = ['cup', 'dash', 'can', 'pack', 'pint', 'teaspoon', 'tablespoon', 'pound', 'ounce', 'pinch', 
                    'clove', 'stalk', 'slices', 'inch']
    time_units = ['second', 'minute', 'hour']

    #  Corrections for the NLTK part-of-speech tagger; can just update this while testing on various recipes
    JJ_corrections = ['small', 'medium', 'large', 'brown']
    VB_corrections = ['combine', 'coat', 'cook', 'stir', 'drain', 'toss', 'serve', 'place', 'heat', 'brush', 'beat', 'bake',
                      'mix', 'cut']
    VBD_corrections = ['ground']
    NN_corrections = []
    #  was thinking of puting some stuff like 'extra' / 'to taste' as numbers, but what about like... 'extra-virgin olive oil'
    #  something to consider, I guess
    CD_corrections = []     
    
    #  Some necessary preprocessing because the NLTK part-of-speech tagger is kinda meh sometimes; also to get measurement words
    parts = []
    for t in tuples:
        is_measurement = False
        for m in measurements:
            if m in t[0]:
                is_measurement = True
                break
        is_timeunit = False
        for u in time_units:
            if u in t[0]:
                is_timeunit = True
                break     
        if is_measurement == True:
            parts.append([t[0], 'MEASUREMENT'])
        elif is_timeunit == True:
            parts.append([t[0], 'TIME'])
        elif t[0] in NN_corrections:
            parts.append([t[0], 'NN'])
        elif t[0] in JJ_corrections:
            parts.append([t[0], 'JJ'])
        elif t[0] in VBD_corrections:
            parts.append([t[0], 'VBD'])
        elif t[0] in CD_corrections:
            parts.append([t[0], 'CD'])
        elif t[0] in VB_corrections:
            parts.append([t[0], 'VB'])
        elif t[0][-3:] == "ing":    #   check for missing gerunds
            parts.append([t[0], 'VBG'])
        else:
            parts.append(list(t))
    
    return parts
    
def parse_ingredient(description):
    ing_data = {'name': [], 'quantity': [], 'measurement': [], 'descriptor': [], 'preparation': []}
    tokens = word_tokenize(description)
    
    #  Stuff in parentheses gets auto-chosen as a descriptor
    text = deparenthesize(tokens)[0]
    ing_data['descriptor'] = deparenthesize(tokens)[1]
    parts_tuples = pos_tag(text)
    parts = parts_fix(parts_tuples)
    
    # Classify relevant words based on their part of speech / assigned tag
    i = 0
    while(i < len(parts)):
        # Special case before everything else; the phrase 'to taste' should be a measurement
        if len(parts[i:]) > 1 and parts[i][0] == 'to' and parts[i+1][0] == 'taste':
            ing_data['measurement'].append(parts[i][0])
            ing_data['measurement'].append(parts[i+1][0])
            i = i+1
        # Rest of it is handled as usual, according to modified part-of-speech tags
        if parts[i][1] == 'CD':
            ing_data['quantity'].append(parts[i][0])
        elif parts[i][0] == 'with':     # special case
            ing_data['name'].append(parts[i][0])
        elif parts[i][1] == 'MEASUREMENT':
            ing_data['measurement'].append(parts[i][0])
        elif parts[i][1] == 'RB':
            if parts[i+1][1] == 'VBD' or parts[i+1][1] == 'VBN':
                ing_data['preparation'].append(parts[i][0])
        elif parts[i][1] == 'VBD' or parts[i][1] == 'VBN':
            ing_data['preparation'].append(parts[i][0])
        elif parts[i][1] == 'JJ':
            ing_data['descriptor'].append(parts[i][0])
            if len(parts[i:]) > 1 and (parts[i][0] == 'low' or parts[i][0] == 'high') and (parts[i+1][1] == 'NN' or parts[i+1][1] == 'RB'):
                ing_data['descriptor'].append(parts[i+1][0])
                i = i + 1
        elif parts[i][1] == 'NN' or parts[i][1] == 'NNS' or parts[i][1] == 'NNP' or parts[i][1] == 'VBG':
            ing_data['name'].append(parts[i][0])
        i = i + 1
    return ing_data

def parse_tools(instruction, ingredients, title):  
    #  this actually seemed to improve the identification?? not sure why but will leave it for now
    lowercase = instruction.lower()
    
    # banned words; method is almost perfect, but some common words slip through, so just get rid of them here
    banned_words = ['heat', 'sauce', 'degree', 'shape', 'place', 'time', 'sprinkle', 'back', 'amount', 'direction',
                    'dough']
    
    #  create tokens and assign parts-of-word
    tokens = word_tokenize(lowercase)
    parts_tuples = pos_tag(tokens)
    parts = parts_fix(parts_tuples)
    
    # remove all non-noun words
    parts = [x for x in parts if (x[1] == 'NN' or x[1] == 'NNS') and x[0][-4:] != "ness"]
    title_words = word_tokenize(title)
    for title_word in title_words:
        parts = [x for x in parts if title_word not in x[0] and not misspelling(x[0], title_word)]
    for banned_word in banned_words:
        parts = [x for x in parts if banned_word not in x[0]]
    for ingredient in ingredients:
        parts = [x for x in parts if x[0] != ingredient and not misspelling(x[0], ingredient)] 
    if len(parts) < 1:
        return
    else:
        found_tools = []
        for i in range(0, len(parts)):
            found_tools.append(parts[i][0])
        return found_tools

def full_ingredients_list(ingredients):
    all_ingredients = []
    for ingredient in ingredients:
        all_ingredients = all_ingredients + ingredient['name']
        all_ingredients = all_ingredients + ingredient['measurement']
    return all_ingredients

def misspelling(string1, string2):  # allowing 2-letter difference, for leniency
    mistakes = abs(len(string1) - len(string2))
    for i in range(0, min(len(string1), len(string2))):
        if string1[i] != string2[i]:
            mistakes = mistakes + 1
    return mistakes <= 2

if __name__ == '__main__':
    all_strings = fetch_page(set_url)
    ing_strings = all_strings[0]
    dir_strings = all_strings[1]
    title = all_strings[2]
    ingredients = []
    for ing_string in ing_strings:
        ingredients.append(parse_ingredient(ing_string))
    print(ingredients)
    all_ingredients = full_ingredients_list(ingredients)
    tools = []
    for dir_string in dir_strings:
        print(dir_string)
        parsed_tools = parse_tools(dir_string, all_ingredients, title)
        if parsed_tools != None:
            tools = tools + [x for x in parsed_tools if x != None]
            tools = list(set(tools))
    print(tools)
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    