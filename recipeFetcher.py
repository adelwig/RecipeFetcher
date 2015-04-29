# -*- coding: utf-8 -*-
#
# This is a small python program that goes to the USDA web site
# (http://recipefinder.nal.usda.gov/), downloads all recipes and
# ingredients into a SQLite database (the folder has a working version
# of it called recipes.db) and then serves the web page that takes
# user's input and suggests recipes.
# Anton Delwig; March 2014

import urllib
import sqlite3
from bs4 import BeautifulSoup
import time
import web
from web import form
#import bitarray

# CONSTANTS
COL_PREFIX='ing_'

def getSoup(url_link):
    sock = urllib.urlopen(url_link)
    htmlSource = sock.read()
    sock.close()
    soup = BeautifulSoup(htmlSource)
    return soup

def cleanUpString(inString):
    inString=unicode(str(inString))
    inString=inString.lower() # lower case everything
    inString=inString.partition(',')[0] # keep track of main ingredients only
    inString=inString.partition('(')[0]
#    inString=inString.partition(' in ')[0]
    inString=inString.partition(':')[0]
    inString=inString.partition('&')[0]
    inString=inString.partition('/')[0]
#    inString=inString.partition(' or ')[0]
#    inString=inString.partition(' as ')[0]
#    inString=inString.partition(' with ')[0]
#    inString=inString.partition(' and ')[0]
    inString=inString.strip() # remove trailing white spaces
    return inString
    
# Create tables
answer=raw_input("Fetch new data and overwrite database? [Y/N] (default is N)")
fetch_data=False
if answer.lower()=='y':
    fetch_data=True
elif answer.lower()=='n':
    fetch_data=False

if fetch_data:
    rootURL="http://recipefinder.nal.usda.gov"
    recipesURL=rootURL+"/recipes"
    ingredientsURL=rootURL+"/ingredient-list"

    conn = sqlite3.connect('recipes.db')
    c = conn.cursor()
    
    # create tables
    try:
        c.execute("""
        CREATE TABLE ingredients (
        id integer primary key,
        ingredient text)
        """)
    except sqlite3.Error as e:
        print "An error occurred:", e.message, "  ", e.args[0]
        c.execute("DELETE FROM ingredients")
        #conn.commit()

    try:
        c.execute("""
        CREATE TABLE recipes (
        id integer primary key,
        url text,
        name text)
        """)
    except sqlite3.Error as e:
        print "An error occurred:", e.message, "  ", e.args[0]
        c.execute("DELETE FROM recipes")
        #conn.commit()

    # extract list of ingredients
    # ------------------------------
    soup = getSoup(ingredientsURL)
    i=1
    dictionaryIngredients={} # store ingredients in dictionary data structure
    for link in soup.find_all('a'):
        linkText=str(link.get('href'))
        if linkText.startswith('/ingredient-list/'):
            try:
                ingredient=cleanUpString(link.get_text())
            except:
                # ignore ingredients with non-English characters
                continue

            if ingredient not in dictionaryIngredients:
                dictionaryIngredients[ingredient]=i
                print ingredient
                # write record to SQL database
                c.execute('INSERT INTO ingredients (id, ingredient) VALUES (?,?)', (i, ingredient,))
                # create new column in recipes table for each ingredient
                col_name=COL_PREFIX+str(i)
                sql_statement='ALTER TABLE recipes ADD COLUMN ' + col_name + ' integer default 0'
                c.execute(sql_statement)
                #conn.commit()
                i=i+1
   
    
    # pause between page requests
    print "Done fetching ingredients"
    time.sleep(0.5)
    

    # extract all recipes
    # -------------------------------
    soup = getSoup(recipesURL)

    # figure out how many pages to go through
    lastPage=0
    for link in soup.find_all('a'):
        linkText=str(link.get('href'))
        if linkText.startswith('/recipes?page='):
            # find the highest number
            pageString=str(linkText)
            splitText=pageString.split('=', 1)
            i=int(splitText[1])
            if i>lastPage:
                lastPage=i

    # now, capture all recipes
    j=1 # recipe id
    for i in range(0,lastPage):
        if i>0: # no need to retrieve the first page
            nextURL=recipesURL+'?page='+str(i)
            soup = getSoup(nextURL)

        for link in soup.find_all('a'):
            linkText=str(link.get('href'))
            if linkText.startswith('/recipes/'):
                recipeName=link.get_text()
                # exclude duplicates (works for this website only)
                if  recipeName.find('Read more')==-1:
                    # now, open this link and record name, URL, ingredients, cooking time, cost
                    recipeItemURL=rootURL+linkText
                    soupRecipeItem = getSoup(recipeItemURL)
                    # create new record for this recipe
                    c.execute('INSERT INTO recipes (id, url, name) values (?,?,?)', (j, recipeItemURL,recipeName,))
                    #conn.commit()                
                    # get ingredients
                    z=0 # track number of recognized ingredients
                    zz=0 # track number of all ingredients in the recipe
                    for item in soupRecipeItem.find_all(property="v:name"):
                        zz=zz+1
                        try:
                            ingredient=cleanUpString(item.get_text())
                            sql_select="SELECT id FROM ingredients where ingredient=?"
                            c.execute(sql_select, (ingredient,))
                            sql_result=c.fetchall()
                            if len(sql_result)==1:
                                # we found the match
                                ingredient_id=sql_result[0][0]
                                #ingredient_list.append(ingredient_id)
                                #print ingredient
                                z=z+1
                                # update the ingredient column in the recipes table
                                col_name=COL_PREFIX+str(ingredient_id)
                                #sql_update="UPDATE recipes set ?=1 where id=?"
                                sql_update="UPDATE recipes set " + col_name +"=1 where id=" + str(j)
                                #c.execute(sql_update, (col_name,i,))
                                c.execute(sql_update)
                                #conn.commit()                            
                        except:
                            # ignore ingredients with non-English characters
                            continue  
                    
                    print "page="+str(i)+" | recipe " + str(j) + " | " + recipeName, " |  recognized ingredients: " + str(z) + " out of " + str(zz)
                    j=j+1
                    # pause between page requests
                    time.sleep(0.5)

    conn.commit()
    conn.close()

# now, get input from user, parse ingredients and use SQL to suggest recipes
# alternative implementation - read data into bitarray and perform boolean AND
display_method='web'
answer=raw_input("Use web browser or terminal to search for recipes? [w/t] (default is web)")
if answer.lower()=='w':
    display_method='web'
    print "Open browser and point to localhost:8080"
elif answer.lower()=='t':
    display_method='terminal'
    
if display_method=='terminal':
    conn = sqlite3.connect('recipes.db')
    c = conn.cursor()
    
    ingredients_AND_list=[]
    #columns_tuple=()
    print "Type ingredients you want in the recipe (one at a time)"
    while True:
        user_input=raw_input("""
                    Type in the name of an ingredient and hit Enter.  
                    Type quit to finish: """)
        if user_input.lower()=='quit':
            break
        else:
            ingredient=cleanUpString(user_input)
            # retrieve the recipes with this ingredient
            sql_select="SELECT id FROM ingredients where ingredient like '%"+ingredient+"%'"
            c.execute(sql_select)
            #sql_select="SELECT id FROM ingredients where ingredient=?"
            #c.execute(sql_select, (ingredient,))
            sql_result=c.fetchall()
            if len(sql_result)==0:
                print "No ingredients found. Try again"
            else:
                # we found the match(es)
                ingredients_OR_list=[]
                for item in sql_result:
                    ingredient_id=item[0]
                    ingredients_OR_list.append(ingredient_id)
                ingredients_AND_list.append(ingredients_OR_list)
                sql_text='('
                for each_OR_list in ingredients_AND_list:
                    for item in each_OR_list:
                        col_name=COL_PREFIX+str(item)+"=1 OR "
                        sql_text=sql_text+col_name       
                    # remove trailing text " OR "
                    sql_text=sql_text.rpartition(" OR ")[0] 
                    sql_text=sql_text+")"
                    sql_text=sql_text + " AND ("
                # remove trailing text " AND "
                sql_text=sql_text.rpartition(" AND (")[0]     
                sql_select_recipe="SELECT name, url FROM recipes where " + sql_text
                c.execute(sql_select_recipe)
                sql_result_recipes=c.fetchall()
                if len(sql_result_recipes)==0:
                     print "No recipes found. Try again"
                else:
                    for item in sql_result_recipes:
                        print str(item[0]), str(item[1])
                #for row in c.execute(sql_select_recipe):
                #    print str(row[0]), str(row[1])

    conn.close()                

elif display_method=='web':
    # web version     
    render = web.template.render('templates/')

    urls = ('/', 'index')
    app = web.application(urls, globals())

    db = web.database(dbn='sqlite', db='recipes.db')

    def execute_SQL(sql_statement):
        #c.execute(sql_statement)
        #return c.fetchall()
        #for each in list(result):
        #    print each['id']
        return list(db.query(sql_statement))

    myform = form.Form( 
        form.Textbox("ingredient", value=""),
        form.Textarea("list", description="List of ingredients", value=""),
        form.Dropdown('reset', ['no','yes'], description="Reset ingredients?"),
        #form.Dropdown('sort', ['A-Z','rating','calories','cost','number of ingredients'], description="Sort by"),
        #form.Checkbox('Reset', checked=False),
        form.Button("Update")
        
    )

    ingredients_AND_list=[]
    ingredients_list=[] # keep track of requested ingredients

    class index:
        
        def GET(self): 
            f = myform()
            #recipes = execute_SQL("SELECT name, url FROM recipes where ing_1=1")
            # make sure you create a copy of the form by calling it (line above)
            # Otherwise changes will appear globally
            return render.main(f, [])

        def POST(self): 
            f = myform()
            if f.validates(): 
                # form.d.boe and form['boe'].value are equivalent ways of
                # extracting the validated arguments from the form.
                #return "Grrreat success! boe: %s, bax: %s" % (form.d.boe, form['bax'].value)
                print f['reset'].value
                if f['reset'].value=='yes':
                    f['reset'].value='no'
                    del ingredients_AND_list[:]
                    del ingredients_list[:]
                    f['list'].value=''
                    return render.main(f, [])
                else:                   
                    ingredient_text=f.d.ingredient
                    ingredient=cleanUpString(ingredient_text)
                    sql_select="SELECT id FROM ingredients where ingredient like '%"+ingredient+"%'"
                    #c.execute(sql_select)
                    #sql_result=c.fetchall()
                    sql_result=execute_SQL(sql_select)
                    if len(sql_result)==0:
                        print "No ingredients found. Try again."
                    else:
                        # we found the match(es)
                        ingredients_OR_list=[]
                        for item in sql_result:
                            #ingredient_id=item[0]
                            ingredient_id=item['id']
                            ingredients_OR_list.append(ingredient_id)
                        ingredients_AND_list.append(ingredients_OR_list)
                        sql_text='('
                        for each_OR_list in ingredients_AND_list:
                            for item in each_OR_list:
                                col_name=COL_PREFIX+str(item)+"=1 OR "
                                sql_text=sql_text+col_name       
                            # remove trailing text " OR "
                            sql_text=sql_text.rpartition(" OR ")[0] 
                            sql_text=sql_text+")"
                            sql_text=sql_text + " AND ("
                        # remove trailing text " AND "
                        sql_text=sql_text.rpartition(" AND (")[0]     
                        sql_select_recipe="SELECT name, url FROM recipes where " + sql_text
                        recipes = execute_SQL(sql_select_recipe)
                        # update fields on the page
                        ingredients_list.append(ingredient)
                        f['list'].value=', '.join(ingredients_list)
                        f['ingredient'].value=''
                        return render.main(f, recipes)
            
    web.internalerror = web.debugerror
    app.run()

