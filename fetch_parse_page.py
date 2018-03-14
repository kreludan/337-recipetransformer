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

https://www.allrecipes.com/recipe/19485/honey-grilled-shrimp/
Possible issue with 'garlic powder' being labeled as powder with a garlic descriptor. 'Shrimp, with tails attached' have 'attached' 
falling under preparation. Added skewers, refrigerator, freezer, to tools list

Tool parser testing; initially for the tool parser tried an approach that made use of part-of-word, but it was running into some--
--issues, so eventually just settled for a simpler approach that searches from a list of already-known tool words. Will just keep--
--updating this to make it more extensive and applicable to a variety of recipes.

For not healthy to healthy, can use the following food 'hacks':
    - https://www.goredforwomen.org/live-healthy/heart-healthy-cooking-tips/healthy-substitutions/
    - https://www.nhlbi.nih.gov/health/educational/lose_wt/eat/shop_lcal_fat.htm
    - https://www.swansonvitamins.com/blog/natural-health-tips/food-replacement-hacks
"""

from bs4 import BeautifulSoup
import urllib.request
from nltk import pos_tag, word_tokenize
import copy
import string
import sys
from nltk.stem.porter import *
#   For now, the URL has to be manually changed here
#   Ideally by the end we'll have some walkthrough / user input interface which will be nicer
# set_url = "https://www.allrecipes.com/recipe/242314/browned-butter-banana-bread/"
# set_url = "https://www.allrecipes.com/recipe/234534/beef-and-guinness-stew/?internalSource=hub%20recipe&referringContentType=search%20results&clickId=cardslot%202"
# set_url = 'https://www.allrecipes.com/recipe/220128/chef-johns-buttermilk-fried-chicken/?internalSource=staff%20pick&referringId=650&referringContentType=recipe%20hub'
# set_url ='https://www.allrecipes.com/recipe/16669/fried-chicken-tenders/?internalSource=staff%20pick&referringId=650&referringContentType=recipe%20hub'
# set_url = 'https://www.allrecipes.com/recipe/8970/millie-pasquinellis-fried-chicken/?internalSource=hub%20recipe&referringId=650&referringContentType=recipe%20hub'
set_url = "https://www.allrecipes.com/recipe/8778/cajun-chicken-pasta/?internalSource=staff%20pick&referringId=1981&referringContentType=recipe%20hub"
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
    measurement_bans = ['canola']
    time_units = ['second', 'minute', 'hour']

    #  Corrections for the NLTK part-of-speech tagger; can just update this while testing on various recipes
    JJ_corrections = ['small', 'medium', 'large']
    VBD_corrections = ['ground']
    VB_corrections = ['combine', 'coat', 'cook', 'stir', 'drain', 'toss', 'serve', 'place', 'brush', 'beat', 'bake',
                      'mix', 'cut', 'baste', 'grill', 'thread', 'roast','stewing','stew','boil','grill', 'arrange', 'fry',
                      'heat','saute','steam']
    NN_corrections = ['garlic']  #  really not sure why this one's an issue...
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
        if t[0] in measurement_bans:
            is_measurement = False
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
    ingredient_banned_words = ['piec','fri','bake','boil','grill', 'thread', 'roast','stewing','stew','grill']
    #  Stuff in parentheses gets auto-chosen as a descriptor
    text = deparenthesize(tokens)[0]
    ing_data['descriptor'] = deparenthesize(tokens)[1]
    parts_tuples = pos_tag(text)
    parts = parts_fix(parts_tuples)
    
    vbp_words = ['cumin', 'canola']  # edge case; to account for
    
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
        elif 'JJ' in parts[i][1] or (parts[i][1] == 'VBP' and parts[i][0] in vbp_words):
            ing_data['descriptor'].append(parts[i][0])
            if len(parts[i:]) > 1 and (parts[i][0] == 'low' or parts[i][0] == 'high') and (parts[i+1][1] == 'NN' or parts[i+1][1] == 'RB'):
                ing_data['descriptor'].append(parts[i+1][0])
                i = i + 1
        elif parts[i][1] == 'NN' or parts[i][1] == 'NNS' or parts[i][1] == 'NNP' or parts[i][1] == 'VBG':
            single_ingre = depluralize([parts[i][0]])[0]
            if single_ingre not in ingredient_banned_words:
                ing_data['name'].append(single_ingre)
        i = i + 1
    return ing_data

def misspelling(string1, string2):  # allowing 2-letter difference, for leniency
    mistakes = abs(len(string1) - len(string2))
    for i in range(0, min(len(string1), len(string2))):
        if string1[i] != string2[i]:
            mistakes = mistakes + 1
    return mistakes <= 1

def remove_plurals(tools):      # if we have 'spoon' and 'spoons', keep 'spoon' only
    for i in range(0, len(tools)):
        for j in range(i, len(tools)):
            if tools[i] == tools[j] + 's':
                tools[i] = tools[j]
            elif tools[j] == tools[i] + 's':
                tools[j] = tools[i]

def remove_tool_as_verb(tools):      # if we have 'grill' and 'grilling', keep 'grill' only
    for i in range(0, len(tools)):
        for j in range(i, len(tools)):
            if tools[i] == tools[j] + 'ing':
                tools[i] = tools[j]
            elif tools[j] == tools[i] + 'ing':
                tools[j] = tools[i]

def full_ingredients_list(ingredients):
    all_ingredients = []
    for ingredient in ingredients:

        all_ingredients = all_ingredients + ingredient['name']
    return all_ingredients

def infer_tools(instruction):
    lowercase = instruction.lower()
    tokens = word_tokenize(lowercase)
    return infer_tools_helper(tokens)

def infer_tools_helper(tokens):
    #dictionary of inferred tools to tool
    inferred_tools = {'stirring spoon': ['mix', 'stir'], 'strainer': ['drain', 'strain'], 'knife': ['cut', 'chop', 'dice', 'mince'],
                      'refrigerator': ['chill', 'refrigerate'], 'sifter': ['sift']}


    result_tools = []
    for token in tokens:
        for key in inferred_tools.keys():
            if token in inferred_tools[key]:
                result_tools.append(key)

    return result_tools

  
def parse_tools(instruction):
    #  banning some words that slip through the cracks
    banned_words = ['potato', 'pinch', 'scraping']
    
    #  doing this the old way seemed to not be so great; so I think I'll just keep a running list of tool words instead
    tool_words = ['pan', 'skillet', 'pot', 'sheet', 'grate', 'whisk', 'spoon', 'cutter', 'board', 'oven', 'bowl', 'bag',
                  'towel', 'pin', 'knife', 'masher', 'skewer', 'refrigerator', 'freezer', 'grill', 'ladle', 'pour', 'simmer']
    
    lowercase = instruction.lower()
    #  since we're just searching for words, we shouldn't need part-of-word information, just tokens
    tokens = word_tokenize(lowercase)

    #  keep all words with tool words in them (including subsets; e.g. 'saucepan')
    potential_tools = []
    for token in tokens:
        for tool_word in tool_words:
            if tool_word in token:
                potential_tools.append(token)
                break
    found_tools = []
    for potential_tool in potential_tools:
        is_tool = True
        for banned_word in banned_words:
            if banned_word in potential_tool:
                is_tool = False
                break
        if is_tool:
            found_tools.append(potential_tool)
    return found_tools

def parse_methods(instruction, ingredients):
    # keeping a list of banned words
    banned_words = ['be', 'is', 'set']
    list_of_methods = ['combine', 'coat', 'cook', 'stir', 'drain', 'toss', 'serve', 'place', 'brush', 'beat', 'bake',
                      'mix', 'cut', 'baste', 'grill', 'thread', 'roast','stewing','stew','boil','grill', 'arrange', 'fry',
                      'heat','saute','steam']
    lowercase = instruction.lower()
    tokens = word_tokenize(lowercase)
    parts_tuples = pos_tag(tokens)
    parts = parts_fix(parts_tuples)
    found_methods = []
    for part in parts:
        if 'VB' == part[1] and part[0] not in ingredients and part[0] in list_of_methods:
            found_methods.append(part[0])
        # This part was added because I found some of the method are recognized as NN ——YW
        if 'NN' == part[1] and part[0] in list_of_methods:
            found_methods.append(part[0])

    return found_methods

def infer_methods(method_word,tools):   
    #print(tool_names)
    combined_list = method_word+tools
    inferred_methods = []
    #These rules need to be updated to incorperate more cases 
    rules = {('cook','skillet','oil'):'fry',('grill'):'grill',('pot','water'):'boil',
    ('drain','pot'):'boil'}
    for key_words in rules.keys():
        common_words = [word for word in combined_list if word in key_words]
        #match the rule, append the val from the dict
        if len(common_words) == len(key_words):
            inferred_methods.append(rules[key_words])

    return inferred_methods

def find_ingredients_objects(ing_strings):
    ingredients = []
    for ing_string in ing_strings:
        ingredients.append(parse_ingredient(ing_string))
    return ingredients

def full_tools_list(dir_strings):
    all_tools = {'parsed_tools': [], 'inferred_tools': []}
    parsed_tools = []
    inferred_tools = []
    for dir_string in dir_strings:
        parsed_tools = parsed_tools + parse_tools(dir_string)
        inferred_tools = inferred_tools + infer_tools(dir_string)
    remove_plurals(parsed_tools)
    remove_tool_as_verb(parsed_tools)
    remove_plurals(inferred_tools)
    remove_tool_as_verb(inferred_tools)
    all_tools['parsed_tools'] = list(set(parsed_tools))
    all_tools['inferred_tools'] = list(set(inferred_tools))
    return all_tools

def full_methods_list(dir_strings, all_ingredients):
    all_methods = {'parsed_methods': [], 'inferred_methods': []}
    parsed_methods = []
    for dir_string in dir_strings:
        parsed_methods = parsed_methods + parse_methods(dir_string, all_ingredients)
    all_methods['parsed_methods'] = list(set(parsed_methods))
    all_tools = full_tools_list(dir_strings)
    all_methods['inferred_methods'] = list(set(infer_methods(all_methods['parsed_methods'], all_tools['parsed_tools'] + all_tools['inferred_tools'])))
    return all_methods

def assemble_instruction_objects(dir_strings, all_ingredients):
    instruction_objects = []
    tools_list = []
    methods_list = []
    inferred_methods  = []
    for dir_string in dir_strings:
        instruction_object = {'ingredients': [], 'parsed_tools': [], 'inferred_tools': [], 'parsed_methods': [], 'inferred_methods': [],
        'primary_method':[],'other_method':[]}
        instruction_object['ingredients'] = list(set(find_instruction_ingredients(dir_string, all_ingredients)))
        instruction_object['parsed_tools'] = list(set(parse_tools(dir_string)))
        instruction_object['inferred_tools'] = list(set(infer_tools(dir_string)))
        tools_list = tools_list + instruction_object['parsed_tools'] + instruction_object['inferred_tools']
        instruction_object['parsed_methods'] = list(set(parse_methods(dir_string, all_ingredients)))
        methods_list = methods_list + instruction_object['parsed_methods']
        potentially_inferred = list(set(infer_methods(methods_list, tools_list)))
        instruction_object['inferred_methods'] = [method for method in potentially_inferred if method not in inferred_methods]
        classified_method = find_primary_cooking_method(instruction_object['inferred_methods']+instruction_object['parsed_methods'] )
        instruction_object['primary_method'] = classified_method['primary_method']
        instruction_object['other_method'] = classified_method['other_method']

        inferred_methods = inferred_methods + instruction_object['inferred_methods']
        instruction_objects.append(instruction_object)
    return instruction_objects
    
def find_instruction_ingredients(instruction, all_ingredients):
    ingredients_list = []
    tokens = word_tokenize(instruction)
    for ingredient in all_ingredients:
        for token in tokens:
            if token == ingredient or misspelling(token, ingredient):
                ingredients_list.append(token)
                break
    return list(set(ingredients_list))

def find_primary_cooking_method(all_methods):
    primary_cooking_method = ['bake','steam','grill','roast','boil','stew','fry','saute',
    'poach','broil']
    primary_cooking = []
    other_cooking = []
    method = {'primary_method':[],'other_method':[]}
    for me in all_methods:
        if me in primary_cooking_method:
            primary_cooking.append(me)
        else:
            other_cooking.append(me)
    method['primary_method'] = list(set(primary_cooking))
    method['other_method'] = list(set(other_cooking))
    return method

'''
CUSTOM TRANSFORM:
Regular recipe ---> South Asian food!!! Gotta do it for the culture (':
Transform rules (for documentation's sake):
(1.) Kinda the golden rule for Hindus is No Cow Meat Allowed; goat or lamb are pretty reasonable replacements
---Brown folks (especially Muslim folks) don't really eat pork like that tbh... might need to change that as well
---Maybe cow --> lamb, pork --> goat??? IDK

(2.) Change the oil... olive/canola aren't really things, Mustard oil might be the most reasonable
(3.) If it's a savory dish, gotta do the following;
---If cooked, then the spice pantheon; ginger/garlic paste, cumin/turmeric/red chili/coriander powder
---If uncooked, then cumin seeds, coriander and mint
---The vegetable core; onions, tomatoes, green chili; 1.5x those already included, add 1 of whatever isn't
(4.) If it's a sweet dish, we can give it a ~desi twist~;
---Add some pistachios, and add some saffron
---Sugar should probably be brown sugar?

Changes to the cooking?
---If cooking is involved, then generally you should sear the vegetables before doing anything else with them
---Not sure if this should be included as a preparation in the instructions, or not, though......
'''
def custom_transform(ingredient_objects, instruction_objects, title = "placeholder"):
    banned = ['cow', 'beef', 'steak', 'filet', 'mignon', 'brisket', 'pork']   #  गाय हमारी माता हे !!!! don't eat cows; also pork
    to_modify = ['hotdog', 'ribs']
    ingredients = copy.deepcopy(ingredient_objects)
    
    is_savory = False
    savory_amt = 0  # if it has both sugar and salt, we'll determine if it's savory by seeing which it has more of
    is_sweet = False  #  maybe not the best way to determine it but... idk.
    sweet_amt = 0
    is_cooked = False
    has_onions = False
    has_tomatoes = False
    has_greenchilies = False
    
    savory_measurement = "teaspoons"    #  setting as a default, just in case
    sweet_measurement = "teaspoons"
    
    for ingredient in ingredients:
        
        for banned_word in banned:          #  replaces cow with lamb... will probably need to refine this, huh 
            if banned_word in ingredient['name']:  #  update w/ pork too? 
                ingredient['name'] = ['lamb']
        
        for mod_word in to_modify:
            if mod_word in ingredient['name']:  #  gotta qualify the ingredient as being a lamb replacement
                ingredient['descriptor'] = ['lamb']

        if 'oil' in ingredient['name'] and 'salad' not in title:   # people be putting olive oil in their salads, huh...
            ingredient['name'] = ['oil']
            ingredient['descriptor'] = ['mustard']
            is_cooked = True
        if 'salt' in ingredient['name'] or 'pepper' in ingredient['name']:
            is_savory = True
            savory_amt = savory_amt + convert_to_number(ingredient['quantity'])
            savory_measurement = ingredient['measurement']
        if 'sugar' in ingredient['name']:
            ingredient['descriptor'] = ['brown']
            banned_sugar = ['refined', 'powdered']
            to_delete = []
            for i in range(0, len(ingredient['preparation'])):
                if ingredient['preparation'][i] in banned_sugar:   # no refined / powdered sugar in this house!!
                    to_delete.append(i)
            if len(to_delete) > 0:
                for index in to_delete:
                    del ingredient['preparation'][index]
            is_sweet = True
            sweet_amt = sweet_amt + convert_to_number(ingredient['quantity'])
            sweet_measurement = ingredient['measurement']
        if 'tomato' in ingredient['name'] or 'tomatoes' in ingredient['name']:
            has_tomatoes = True
            ingredient['quantity'] = str(convert_to_number(ingredient['quantity']) * 1.5)
        if 'onion' in ingredient['name'] or 'onions' in ingredient['name']:
            has_onions = True
            ingredient['quantity'] = str(convert_to_number(ingredient['quantity']) * 1.5)
        if ('chili' in ingredient['name'] or 'chilies' in ingredient['name']) and 'green' in ingredient['descriptor']:
            has_greenchilies = True
            ingredient['quantity'] = str(convert_to_number(ingredient['quantity']) * 1.5)
        if 'lettuce' in ingredient['name']:
            ingredient['name'] = 'cabbage'
        # sauce / seasoning changes
        for name in ingredient['name']:
            if 'ponzu' == name:
                name == 'chili'
                break
            if 'hoisin' == name:
                name == 'tamarind'
                break
            if ('soy' == name or 'soya' == name) and 'sauce' in ingredient['name']:
                name == 'sriracha'
                break
            if 'barbecue' == name:
                name == 'indian barbecue'
            if 'cajun' == name:
                name == 'indian'
    # Determine whether or not savory, for ingredient additions
    
    if is_savory and (not is_sweet or (savory_amt >= sweet_amt)):   # savory case
        if is_cooked:
            spice_amounts = str(savory_amt / 2)
            base_string = spice_amounts + ' ' + savory_measurement + ' '
            south_indian_spices = ['ginger paste', 'garlic paste', 'cumin powder', 'turmeric powder', 'red chili powder', 'coriander powder'] ## NOTE THAT SHOULD SEARCH FOR THESE IN THE RECIPE FIRST, SO NO DOUBLE-INGRED.
            for spice in south_indian_spices:
                ingredients.append(parse_ingredient(base_string + spice))
        else:
            south_indian_leaves = ['coriander leaves', 'mint leaves']
            ingredients.append(parse_ingredient('2 teaspoons cumin seeds'))
            for leaf in south_indian_leaves:
                ingredients.append(parse_ingredient('2 tablespoons ' + leaf))

        if not has_tomatoes:
            ingredients = ingredients + parse_ingredient('2 diced tomatoes')
        if not has_onions:
            ingredients = ingredients + parse_ingredient('2 diced onions')
        if not has_greenchilies:
            ingredients = ingredients + parse_ingredient('2 diced green chilies')

    else:  #  sweet case
        sweet_amounts = str(sweet_amt / 2)
        base_string = sweet_amounts + ' ' + sweet_measurement + ' '
        south_indian_sweets = ['crushed pistachios', 'saffron']
        for sweet in south_indian_sweets:
            ingredients.append(parse_ingredient(base_string + sweet))
    
    instructions = copy.deepcopy(instruction_objects)
    
    first_vessel_instruction = "temp"
    
    for instruction in instructions:
        if first_vessel_instruction == "temp":
            potential_vessels = ['pot', 'pan', 'bowl', 'cooker', 'oven']
            for tool in instruction['parsed_tools']:
                if tool in potential_vessels:
                    first_vessel_instruction = instruction
                    break
                
        ingredient_list = instruction['ingredients']
        for i in range(0, len(ingredient_list)):
            for banned_word in banned:
                if banned_word in ingredient_list[i]:
                    ingredient_list[i] = 'lamb'
                    break
            for mod_word in to_modify:
                if mod_word in ingredient_list[i]:
                    ingredient_list[i] = 'lamb ' + ingredient_list[i]
                    break
            oil_types = ['sunflower', 'canola', 'olive', 'avocado', 'palm', 'bran', 'safflower', 'seed']
            if ingredient_list[i] in oil_types and i < len(ingredient_list) and ingredient_list[i+1] == 'oil':
                ingredient_list[i] = 'mustard'
            if 'lettuce' in ingredient_list[i]:
                ingredient_list[i] = 'cabbage'
            if 'ponzu' in ingredient_list[i]:
                ingredient_list[i] = 'chili'
            if 'hoisin' in ingredient_list[i]:
                ingredient_list[i] = 'tamarind'
            if 'soy' in ingredient_list[i] and i < len(ingredient_list) and ingredient_list[i+1] == 'sauce':
                ingredient_list[i] = 'sriracha'
            if 'barbecue' in ingredient_list[i]:
                ingredient_list[i] = 'indian barbecue'
            if 'cajun' in ingredient_list[i]:
                ingredient_list[i] = 'indian seasoning'
            if is_savory and (not is_sweet or (savory_amt >= sweet_amt)):
                if is_cooked:
                    if ingredient_list[i] == 'salt':
                        ingredient_list[i] = ['salt', 'ginger paste', 'garlic paste', 'cumin powder', 'turmeric powder',
                                       'red chili powder', 'coriander powder']
                else:
                    if ingredient_list[i] == 'cabbage':
                        ingredient_list[i] = ['cabbage', 'coriander leaves', 'mint leaves', 'cumin seeds']
            else:
                if ingredient_list[i] == 'sugar':
                    ingredient_list[i] = ['brown sugar', 'pistachios', 'saffron']

    print(ingredients)
    print(instructions)



def convert_to_number(quantity):  # converts quantity field of ingredient object to an actual number
    total_amount = 0
    has_alpha = False
    for number in quantity:
        if any(c.isalpha() for c in number):
            has_alpha = True
            break
        if '/' in number:
            total_amount = total_amount + (int(number[0])/int(number[2]))
        else:
            total_amount = total_amount + int(number)
    if has_alpha == True and total_amount == 0:  # returns 0 for "to taste" while still returing a value for "2 1/2 plus to taste"
        return 0
    return total_amount

def non_vege_to_vege(ingredient_objects, instruction_objects):
    #    ingredients_objects = find_ingredients_objects(ing_strings)
    #   all_ingredients = full_ingredients_list(ingredients_objects)
    meats = ['bear', 'beef', 'heart', 'liver', 'tongue', 'buffalo', 'bison', 'calf', 'caribou', \
            'steak', 'poultry', 'lamb'\
            'goat', 'ham', 'horse', 'kangaroo', 'lamb', 'moose', 'mutton', 'pork', 'bacon', 'rabbit',\
            'snake', 'squirrel', 'tripe', 'turtle', 'veal', 'venison', 'chicken', 'hen', 'duck', 'emu',\
            'gizzard', 'goose', 'ostrich', 'partridge', 'pheasant', 'quail', 'turkey', 'baloney', 'sausage', 'sausages',\
            'spam']

    fish = ['fish', 'salmon', 'trout', 'bass', 'catfish', 'shrimp', 'cod', 'pollock', 'tilapia', 'clam', 'clams'\
            'crab', 'oyster', 'oysters', 'flounder', 'lobster', 'yellowtail', 'sturgeon', 'octopus', 'squid', 'caviar'\
            'mackerel', 'anchovy', 'anchovies', 'scallop', 'scallops', 'tuna', 'eel', 'crawfish', 'crayfish']

    fats = ['fat', 'lard']

    banned = ['chuck', 'boneless', 'bone']

    # For things like heart, liver, tongue, stomach, intestines
    # only replace that particular buzz word, and ignore all the other parts of the name we
    # are looking at.
    spec_organs_or_misc = ['heart', 'liver', 'tongue', 'stomach', 'intestine']

    # Lentils: fish eggs

    # Seitan: chicken, beef
    #           - Including other types of birds as well

    # Specific replacement for seitan
    spec_replacements = ['beef', 'chicken', 'calf', 'goose', 'ostrich',\
                        'partridge', 'pheasant', 'quail', 'turkey', 'hen', 'duck', 'emu']
    # Tempeh: fish, pork
    # default: tofu

    vegeList = ['tofu', 'tempeh', 'seitan', 'lentils']
    vege = 'tofu'
    
    transformed_instruction = []
    instruction_object_copy = copy.deepcopy(instruction_objects)
    #loop over all intructions
    for instruction in instruction_object_copy:
        prev_ingredient = ''
        vege_ingre = []
        c_ingredients = instruction['ingredients']
        if c_ingredients:
            for c_ingre in c_ingredients:
                c_ingre = c_ingre.lower()
                if depluralize(c_ingre) in meats or depluralize(c_ingre) in fish:
                    if depluralize(c_ingre) in spec_replacements:
                        vege_ingre.append('seitan')
                    elif depluralize(c_ingre) in fish or depluralize(c_ingre) == 'pork':
                        vege_ingre.append('tempeh')
                    elif depluralize(c_ingre) in spec_organs:
                        # get rid of first part of organ name (i.e., pig intestine, cow tongue, etc)
                        vege_ingre.pop()
                        vege_ingre.append('tofu')
                    else:
                        vege_ingre.append('tofu')
                elif depluralize(c_ingre) == 'egg':
                    if prev_ingredient == 'fish' or prev_ingredient in fish:
                        vege_ingre.pop()
                        vege_ingre.append('lentils')
                elif depluralize(c_ingre) in fats:
                    vege_ingre.append('butter')
                else:
                    vege_ingre.append(c_ingre)

                prev_ingredient = c_ingre
        instruction['ingredients'] = vege_ingre
        transformed_instruction.append(instruction)
    #transfer the ingredients list
    for c_ingre in ingredient_objects:
        n = c_ingre['name']
        desc = c_ingre['descriptor']
        prev_ingredient = ''
        for i,string in enumerate(n, 0):
            string = string.lower()

            if depluralize(string) in meats or depluralize(string) in fish:
                # replace with relevant vegetable
                if depluralize(string) in spec_replacements:
                    c_ingre['name'][i] = 'seitan'
                elif depluralize(string) in fish or depluralize(string) == 'pork':
                    c_ingre['name'][i] = 'tempeh'
                elif depluralize(string) in spec_organs_or_misc:
                    c_ingre['name'][i] = 'tofu'
                    c_ingre['name'].pop(i-1)
                else:
                    c_ingre['name'][i] = 'tofu'
            elif depluralize(string) == 'egg':
                if prev_ingredient == 'fish' or prev_ingredient in fish:
                    c_ingre['name'][i] = 'lentils'
                    c_ingre['name'].pop(i-1)
            elif depluralize(string) in fats:
                vege_ingre.append('butter')

                c_ingre['name'][i] = 'tofu'
            elif string.lower() in fats:
                # replace with a vegetarian oil/fat
                c_ingre['name'][i] = 'butter'
            elif string.lower() in banned:
                c_ingre['name'].pop(i)

            prev_ingredient = string

        for i,string in enumerate(desc, 0):
            if depluralize(string.lower()) in meats or depluralize(string.lower()) in fish:
                # change descriptor, so basically just make it vegetable
                c_ingre['descriptor'][i] = 'vegetable'
            elif string.lower() in banned:
                c_ingre['descriptor'].pop(i)

    return transformed_instruction,ingredient_objects

def vege_to_non_vege(ingredient_objects, instruction_objects):
    #    ingredients_objects = find_ingredients_objects(ing_strings)
    #   all_ingredients = full_ingredients_list(ingredients_objects)
    # Replace tofu with beef
    # Replace tempeh with pork
    # Replace lettuce/spinach with baconnnnnn
    # if nothing replaced, go ahead and add some crumbled up bacon strips
    
    #     ing_data = {'name': [], 'quantity': [], 'measurement': [], 'descriptor': [], 'preparation': []}

    transformed_instruction = []
    instruction_object_copy = copy.deepcopy(instruction_objects)
    #loop over all intructions
    for instruction in instruction_object_copy:
        prev_ingredient = ''
        full_ingre = []
        meat_ingre = []
        c_ingredients = instruction['ingredients']
        if c_ingredients:
            for c_ingre in c_ingredients:
                c_ingre = c_ingre.lower()
                if depluralize(c_ingre) == 'tofu':
                    meat_ingre.append('beef')
                    full_ingre.append('beef')
                elif depluralize(c_ingre) == 'tempeh':
                    meat_ingre.append('pork')
                    full_ingre.append('pork')
                elif depluralize(c_ingre) == 'lettuce' or depluralize(c_ingre) == 'spinach':
                    meat_ingre.append('bacon')
                    full_ingre.append('bacon')
                elif depluralize(c_ingre) == 'broccoli' or depluralize(c_ingre) == 'eggplant' or depluralize(c_ingre) == 'mushroom':
                    meat_ingre.append('chicken')
                    full_ingre.append('chicken')
                else:
                    full_ingre.append(c_ingre)

            if not meat_ingre:
                full_ingre.append('bacon')


        instruction['ingredients'] = full_ingre
        transformed_instruction.append(instruction)
    #transfer the ingredients list
    for c_ingre in ingredient_objects:
        n = c_ingre['name']
        desc = c_ingre['descriptor']
        for i,string in enumerate(n, 0):
            string = string.lower()

            if depluralize(string) == 'tofu':
                c_ingre['name'][i] = 'beef'
                c_ingre['descriptor'] = []
            elif depluralize(string) == 'tempeh':
                c_ingre['name'][i] = 'pork'
                c_ingre['descriptor'] = []
            elif depluralize(string) == 'lettuce' or depluralize(c_ingre) == 'spinach':
                c_ingre['name'][i] = 'bacon'
                c_ingre['descriptor'] = []
            elif depluralize(c_ingre) == 'broccoli' or depluralize(c_ingre) == 'eggplant' or depluralize(c_ingre) == 'mushroom':
                c_ingre['name'][i] = 'chicken'
                c_ingre['descriptor'] = []

    # if we never replace things, go ahead and add bacon bits to it
    # because bacon goes well with 'everything'


    return transformed_instruction,ingredient_objects



'''
Second Custom Style Tranformation:
Recipe -> Italian Recipe

1. Want to detect if a recipe is already italian
	-Return the same recipe
2. Replace rice with pasta/risotto as necessary
3. Generally all types of protein can stay, could have a catch for some various specific meats and 
replace with 'Italian Sausage'
4. Oil used should almost always use olive oil
5. If cheese is used, could change into a three cheese medley 
6. Eliminate (and replace) foreign spices
	-Foreign spice list = 'Cajun Seasoning', 'Creole Seasoning', 'Cumin', 'Cayenne', 'Curry', 'Saffron', ' Cilantro', 'Taco Seasoning' 
	-Italian spice list = 'Basil', 'Bayleaves', 'Sage', 'Rosemary', 'Marjoram' 'Garlic', 'Onion', 'Oregano', 'Parsley', 'Thyme'
7. Eliminate (and replace) foreign sauces
	-Foreign sauce list = 'Ponzu', 'Hoisin', 'Soy', 'Sweet and Sour', 'Teriyaki', 'Sriracha', 'Barbecue'
	-Italian sauce list = 'Pesto', 'Alfredo', 'Marinara', 'Vodka (Sauce)', 'Tomato (Sauce)', 'Meat-Based Sauces', 'Neapolitan'
8. Savory dishes to consider
	-Soups -> Italian Soup
	-Anything with a Tortilla -> Pizza
9. Sweet dishes to consider 
	-

'''     

def italian_transform(ingredient_objects, instruction_objects,title = "placeholder",):

	foreign_spices = ['Cajun Seasoning', 'Creole Seasoning', 'Cumin', 'Cayenne', 'Curry', 'Saffron', ' Cilantro', 'Taco Seasoning']  
	foreign_sauces = ['Ponzu', 'Hoisin', 'Soy', 'Sweet and Sour', 'Teriyaki', 'Sriracha', 'Barbecue']
	foreign_proteins = []

	ingredients = copy.deepcopy(ingredient_objects)



def depluralize(ingredient):
    if ingredient == 'cheeses':
        return 'cheese'
    elif ingredient[-3:] == 'ies':
        return ingredient[:-3] + 'y'
    elif ingredient[-2:] == 'es':
        return ingredient[:-2]
    elif ingredient[-1:] == 's':
        return ingredient[:-1]
    else:
        return ingredient

def non_heal_to_heal(ingredient_objects, instruction_objects):
    """
    Substitutes to consider:
        Rice -> Quinoa                  (150% more fiber and protein for same serving)
        Mayo -> Mustard                 (mustard has no sugar or saturated fat, compared to mayo)
        Sour Cream -> Greek Yogurt      (half the calories, 3x the protein)
        Croutons -> Almonds             (1/3 carbs, 2x protein, 3x fiber)
        Flour -> Coconut flour          (fewer carbs, 11x fiber)
        Chocolate -> Cacao / cacao nibs (no sugar, 5x fiber)
        Bread crumbs -> chia seeds      (19x fiber, 2x protein, 1/35th sodium)
        Peanut butter -> almond butter  (no hydrogenated vegetable oils or added sugar)
        Milk -> Skim Milk / Almond Milk (Almond Milk has less sugar and more calcium, Skim Milk has less fat)
        Cheese -> fat free cheese       (self explanatory)
        Eggs -> egg whites              (will typically need 2x as much eggs to get the same portion size)
                                        (lower cholestrol basically)
        lettuce -> spinach/arugula
        butter/oil -> 1/2 canola oil, 1/2 unsweetened applesauce

        Instruction object layout for reference
        instruction_object = {'ingredients': [], 'parsed_tools': [], 'inferred_tools': [], 'parsed_methods': [], 'inferred_methods': [],
        'primary_method':[],'other_method':[]}
    """
    transformed_instruction = []

    found_sour_cream = False
    #transfer the ingredients list
    for c_ingre in ingredient_objects:
        n = c_ingre['name']
        desc = c_ingre['descriptor']
        for i,string in enumerate(n, 0):
            string = string.lower()
            if depluralize(string) == 'cream' and 'sour' in desc:
                c_ingre['name'][i] = 'yogurt'
                map(lambda x:x if x != 'sour' else 'greek',c_ingre['descriptor'])
            elif depluralize(string) == 'cheese' or depluralize(string) == 'chees':
                c_ingre['descriptor'].append('low-fat')
            elif depluralize(string) == 'peanut':
                c_ingre['name'][i] = 'almond'
                # in general should be healthier, so can replace peanuts with almonds in general
            elif depluralize(string) == 'flour':
                c_ingre['name'] = ['coconut', 'flour']
            elif depluralize(string) == 'lettuce':
                c_ingre['name'] = ['spinach']
            elif depluralize(string) in ['sugar', 'salt']:
                val = convert_to_number(c_ingre['quantity'])
                val = val / 2
                # just half the level of salt and level of sugar
                c_ingre['quantity'] = ['{0}'.format(val)]
            elif depluralize(string) == 'butter' or depluralize(string) == 'oil':
                # Change fat type and decrease it by 25%
                c_ingre['name'] = ['oil']
                c_ingre['descriptor'] = ['extra-virgin', 'olive']
                val = convert_to_number(c_ingre['quantity'])
                val = (val*3)/4
                c_ingre['quantity'] = ['{0}'.format(val)]

    instruction_object_copy = copy.deepcopy(instruction_objects)
    #loop over all intructions
    for instruction in instruction_object_copy:
        healthy_ingredients = []
        c_ingredients = instruction['ingredients']
        if c_ingredients:
            for c_ingre in c_ingredients:
                c_ingre = c_ingre.lower()
                if depluralize(c_ingre) == 'rice':
                    healthy_ingredients.append('quinoa')
                elif depluralize(c_ingre) == 'mayo' or depluralize(c_ingre) == 'mayonnaise':
                    healthy_ingredients.append('mustard')
                elif depluralize(c_ingre) == 'chocolate':
                    healthy_ingredients.append('cacao')
                elif depluralize(c_ingre) == 'crouton' or depluralize(c_ingre) == 'peanut':
                    healthy_ingredients.append('almond')
                elif depluralize(c_ingre) == 'lettuce':
                    healthy_ingredients.append('spinach')
                elif found_sour_cream and depluralize(c_ingre) == 'cream':
                    healthy_ingredients.append('yogurt')                    
                else:
                    healthy_ingredients.append(c_ingre)

                #elif depluralize(c_ingre) == 'sour':
                #    healthy_ingredients.append('greek')
                #elif depluralize(c_ingre) == 'cream':
                #    if healthy_ingredients[-1] == 'greek':
                #        healthy_ingredients.append('yogurt')
                #    else:
                #        healthy_ingredients.append(c_ingre)

        instruction['ingredients'] = healthy_ingredients
        transformed_instruction.append(instruction)

    return transformed_instruction,ingredient_objects

def heal_to_non_heal(ingredient_objects, instruction_objects):
    transformed_instruction = []

    found_sour_cream = False
    #transfer the ingredients list
    for c_ingre in ingredient_objects:
        n = c_ingre['name']
        desc = c_ingre['descriptor']
        for i,string in enumerate(n, 0):
            string = string.lower()
            if depluralize(string) == 'yogurt' or depluralize(string) == 'yoghurt':
                c_ingre['name'] = ['cream']
                c_ingre['descriptor'] = ['sour']
            elif depluralize(string) == 'cheese':
                map(lambda x:x if x != 'low-fat' else 'full-fat',c_ingre['descriptor'])
                if not 'full-fat' in c_ingre['descriptor']:
                    c_ingre['descriptor'].append('full-fat')
            elif depluralize(string) == 'almond':
                c_ingre['name'][i] = 'peanut'
                # in general should be healthier, so can replace peanuts with almonds in general
            elif depluralize(string) == 'rice' or depluralize(string) == 'quinoa':
                c_ingre['name'][i] = 'rice'
                c_ingre['descriptor'] = ['processed']
            elif depluralize(string) == 'flour':
                c_ingre['name'] = ['flour']
                c_ingre['descriptor'] = ['white']
            elif depluralize(string) == 'spinach' or depluralize(string) == 'aragula' or depluralize(string) == 'cabbage':
                c_ingre['name'] = ['lettuce']
                c_ingre['descriptor'] = ['romaine']
            elif depluralize(string) in ['sugar', 'salt']:
                val = convert_to_number(c_ingre['quantity'])
                val = val * 2
                # just half the level of salt and level of sugar
                c_ingre['quantity'] = ['{0}'.format(val)]
            elif depluralize(string) == 'butter' or depluralize(string) == 'oil':
                # Change fat type and increase it by 25%
                c_ingre['name'] = ['lard']
                c_ingre['descriptor'] = []
                val = convert_to_number(c_ingre['quantity'])
                val = (val*4)/3
                c_ingre['quantity'] = ['{0}'.format(val)]

    instruction_object_copy = copy.deepcopy(instruction_objects)
    #loop over all intructions
    for instruction in instruction_object_copy:
        not_healthy_ingredients = []
        c_ingredients = instruction['ingredients']
        if c_ingredients:
            for c_ingre in c_ingredients:
                c_ingre = c_ingre.lower()
                if depluralize(c_ingre) == 'quinoa':
                    not_healthy_ingredients.append('rice')
                elif depluralize(c_ingre) == 'mustard':
                    not_healthy_ingredients.append('mayonnaise')
                elif depluralize(c_ingre) == 'cacao':
                    not_healthy_ingredients.append('chocolate')
                elif depluralize(c_ingre) == 'almond':
                    not_healthy_ingredients.append('crouton')
                elif depluralize(c_ingre) == 'spinach' or depluralize(string) == 'aragula' or depluralize(string) == 'cabbage':
                    not_healthy_ingredients.append('lettuce')
                elif depluralize(c_ingre) == 'oil' or depluralize(c_ingre) == 'butter':
                    not_healthy_ingredients.append('lard')
                elif found_sour_cream and (depluralize(c_ingre) == 'yogurt' or depluralize(c_ingre) == 'yoghurt'):
                    not_healthy_ingredients.append('cream')                    
                else:
                    not_healthy_ingredients.append(c_ingre)

        instruction['ingredients'] = not_healthy_ingredients
        transformed_instruction.append(instruction)

    return transformed_instruction,ingredient_objects 

def generate_ingredient_string(ing):
    special_case = False
    ing_fields = [ing['measurement'], ing['descriptor'], ing['preparation'], ing['name']]
    if ing['measurement'] == ['to', 'taste']:
        special_case = True
    temp = []
    for field in ing_fields:
        temp.append("".join([" "+i if not i.startswith("'") and i not in string.punctuation else i for i in field]).strip())
    ing_string = "".join([" "+i if not i.startswith("'") and i not in string.punctuation else i for i in temp]).strip()
    if special_case:
        return ing_string + ", to taste"
    else:
        return str(convert_to_number(ing['quantity'])) + " " + ing_string


if __name__ == '__main__':
    url = input("Enter a URL from AllRecipes.com, to transform:")
    all_strings = fetch_page(url)
    ing_strings = all_strings[0]
    dir_strings = all_strings[1]
    title = all_strings[2]
    print("Recipe title: " + title)
    print("Finding ingredients objects:")    
    ingredients_objects = find_ingredients_objects(ing_strings)
    print(ingredients_objects)
    all_ingredients = full_ingredients_list(ingredients_objects)
    print (all_ingredients)
    print("Finding all tools list:")
    all_tools = full_tools_list(dir_strings)
    print(all_tools)
    print("Finding all methods list:")
    all_methods = full_methods_list(dir_strings, all_ingredients)
    print(all_methods)
    all_methods_class= find_primary_cooking_method(all_methods['parsed_methods']+all_methods['inferred_methods'])
    print(all_methods_class)
    print("Creating instruction object for each instruction:")
    instructions_objects = assemble_instruction_objects(dir_strings, all_ingredients)
    
    transformed_instructions,transformed_ingredients = non_vege_to_vege(ingredients_objects,instructions_objects)
    for i in range(0, len(dir_strings)):
        print(dir_strings[i])
        print(instructions_objects[i])
        #print(transformed_instructions[i])

    #print(all_ingredients)

    #all_transformed_ingredients = full_ingredients_list(transformed_ingredients)
    #print(transformed_ingredients)
    #print(all_transformed_ingredients)


    
    
    
    
    
    
    
    
    
    
    
    
