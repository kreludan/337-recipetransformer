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


"""

from bs4 import BeautifulSoup
import urllib.request
from nltk import pos_tag, word_tokenize
import copy
#   For now, the URL has to be manually changed here
#   Ideally by the end we'll have some walkthrough / user input interface which will be nicer
# set_url = "https://www.allrecipes.com/recipe/242314/browned-butter-banana-bread/"
# set_url = "https://www.allrecipes.com/recipe/234534/beef-and-guinness-stew/?internalSource=hub%20recipe&referringContentType=search%20results&clickId=cardslot%202"
# set_url = 'https://www.allrecipes.com/recipe/220128/chef-johns-buttermilk-fried-chicken/?internalSource=staff%20pick&referringId=650&referringContentType=recipe%20hub'
# set_url ='https://www.allrecipes.com/recipe/16669/fried-chicken-tenders/?internalSource=staff%20pick&referringId=650&referringContentType=recipe%20hub'
set_url = 'https://www.allrecipes.com/recipe/8970/millie-pasquinellis-fried-chicken/?internalSource=hub%20recipe&referringId=650&referringContentType=recipe%20hub'
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
    JJ_corrections = ['small', 'medium', 'large']
    VBD_corrections = ['ground']
    VB_corrections = ['combine', 'coat', 'cook', 'stir', 'drain', 'toss', 'serve', 'place', 'brush', 'beat', 'bake',
                      'mix', 'cut', 'baste', 'grill', 'thread', 'roast','stewing','stew','boil','grill', 'arrange']
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
    banned_words = ['drain','be', 'is', 'set','cover', 'arrange', 'transfer', 'place','remove','discard', 'turn', 'reduce','combine','raise']
    lowercase = instruction.lower()
    tokens = word_tokenize(lowercase)
    parts_tuples = pos_tag(tokens)
    parts = parts_fix(parts_tuples)
    found_methods = []
    #print(parts)
    for part in parts:
        if 'VB' == part[1] and part[0] not in ingredients and part[0] not in banned_words:
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
        instruction_object = {'ingredients': [], 'parsed_tools': [], 'inferred_tools': [], 'parsed_methods': [], 'inferred_methods': []}
        instruction_object['ingredients'] = list(set(find_instruction_ingredients(dir_string, all_ingredients)))
        instruction_object['parsed_tools'] = list(set(parse_tools(dir_string)))
        instruction_object['inferred_tools'] = list(set(infer_tools(dir_string)))
        tools_list = tools_list + instruction_object['parsed_tools'] + instruction_object['inferred_tools']
        instruction_object['parsed_methods'] = list(set(parse_methods(dir_string, all_ingredients)))
        methods_list = methods_list + instruction_object['parsed_methods']
        potentially_inferred = list(set(infer_methods(methods_list, tools_list)))
        instruction_object['inferred_methods'] = [method for method in potentially_inferred if method not in inferred_methods]
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

def non_vege_to_vege(all_instructions,all_ingredients):
    all_meat = ['beef','fish','goat','lamb','meatball','pork','poultry','sausage','seafood','bacon','ham']
    vege = 'tofu'
    transformed_instruction = []
    all_instructions_copy = copy.deepcopy(all_instructions)
    #loop over all intructions
    for instruction in all_instructions_copy:
        vege_ingre = []
        c_ingredients = instruction['ingredients']
        if c_ingredients:
            for c_ingre in c_ingredients:
                if c_ingre in all_meat:
                    vege_ingre.append(vege)
                else:   
                    vege_ingre.append(c_ingre)
        instruction['ingredients'] = vege_ingre
        transformed_instruction.append(instruction)
    #transfer the ingredients list
    transformed_ingredients = []
    for c_ingre in all_ingredients:
        if c_ingre in all_meat:
            transformed_ingredients.append(vege)
        else:   
            transformed_ingredients.append(c_ingre)
    transformed_ingredients = list(set(transformed_ingredients))      
    return transformed_instruction,transformed_ingredients


def non_heal_to_heal(all_instructions,all_methods):

    pass


if __name__ == '__main__':
    all_strings = fetch_page(set_url)
    ing_strings = all_strings[0]
    dir_strings = all_strings[1]
    title = all_strings[2]
    print("Recipe title: " + title)
    print("Finding ingredients objects:")    
    ingredients_objects = find_ingredients_objects(ing_strings)
    print(ingredients_objects)
    all_ingredients = full_ingredients_list(ingredients_objects)
    print("Finding all tools list:")
    all_tools = full_tools_list(dir_strings)
    print(all_tools)
    print("Finding all methods list:")
    all_methods = full_methods_list(dir_strings, all_ingredients)
    print(all_methods)
    print("Creating instruction object for each instruction:")
    all_instructions = assemble_instruction_objects(dir_strings, all_ingredients)
    transformed_instructions,transformed_ingredients = non_vege_to_vege(all_instructions,all_ingredients)

    for i in range(0, len(dir_strings)):
        print(dir_strings[i])
        print(all_instructions[i])
        print(transformed_instructions[i])
    print(all_ingredients)
    print(transformed_ingredients)

    
    
    
    
    
    
    
    
    
    
    
    