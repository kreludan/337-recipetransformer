# EECS 337 - Recipe Transfomer
Recipe transformer project for Winter 2017 EECS 337.

Team Members:

- David Hofferber
- Vikram Kohli
- Jay Valdillez
- Yixing Wang


## Python 3.6
### Dependencies
- BeautifulSoup 4
  - Installation should be possible via `pip install beautifulsoup4`
- NLTK
  - Installation should be possible via `pip install nltk`
  - nltk.stem.porter is required as well
    - Depending on installation, you may need to run some nltk download commands
      Such installations can be done through the following commands in Python:
      
      ```
      >>> import nltk
      >>> nltk.download('all')
      ```
      
      If there are any missing dependencies that weren't covered by this, then an error will be thrown that specifies the exact command you need to run in order to properly download the missing NLTK data/classes.
     
     
All the code for this project is in a singular file. Recipes can be inputted by initially running the script, and user input will be requested after running it. This is done by giving the AllRecipes url in the default URL format of https://www.allrecipes.com/recipe/8778, where 8778 could be any recipe number hosted on the AllRecipes website.
