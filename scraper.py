#Necessary libraries
import pandas as pd
import numpy as np
import requests
import re
from bs4 import BeautifulSoup

#URL Headers
headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '3600',
    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0'
}

#Scraping list of politicians
politicians = []
url = "https://ballotpedia.org/List_of_current_members_of_the_U.S._Congress"
req = requests.get(url, headers)
soup = BeautifulSoup(req.content, 'html.parser')
pol_table = soup.find_all("table", {"id" : "officeholder-table"})
for element in pol_table:
    rows = element.find_all('tr')
    #Skip headers
    for row in rows[1:]:
        cells = row.find_all('td')
        #Name is second column
        for cell in cells[1]:
            cell = cell.text
            #Remove "Jr./Sr." or middle initials
            cell = re.sub('\s*([A-Z])([a-z])*\.', '', cell)
            politicians.append(cell)

#Scraping list of Hollywood actors
actors = []
url = "https://en.wikipedia.org/wiki/List_of_actors_with_Academy_Award_nominations"
req = requests.get(url, headers)
soup = BeautifulSoup(req.content, 'html.parser')
actor_table = soup.find_all("table", class_="sortable")
for element in actor_table:
    rows = element.find_all('tr')
    #Skip headers
    for row in rows[1:]:
        cells = row.find_all('td')
        #This "~" indicates an empty "died" column; we only want actors that are currently alive
        if cells[3].text == "~":
            #Name is found in the first column
            for cell in cells[0]:
                cell = cell.get_text(strip=True)
                actors.append(cell)

#Scrape musician lists (two sources)
musicians = []
url = "https://www.imdb.com/list/ls058480497/"
req = requests.get(url, headers)
soup = BeautifulSoup(req.content, 'html.parser')
music_table = soup.find_all("h3")
for element in music_table:
    rows = element.find_all('a')
    for row in rows:
        musicians.append(row.get_text(strip=True))
url = "https://www.theguardian.com/news/datablog/2013/apr/19/twitter-music-app-100-most-followed-musicians"
req = requests.get(url, headers)
soup = BeautifulSoup(req.content, 'html.parser')
music_table = soup.find_all("table", class_="in-article sortable")
for element in music_table:
    rows = element.find_all('tr')
    for row in rows[2:]:
        cells = row.find_all('td')
        for cell in cells[2]:
            musicians.append(cell.strip())

#Function to scrape bio from Wikipedia
def scrape_bio(person_name):
    person_name = person_name.replace(" ", "_")  
    url = "https://en.wikipedia.org/wiki/" + person_name
    req = requests.get(url, headers)
    soup = BeautifulSoup(req.content, 'html.parser')
    infobox = soup.find_all("table", class_="infobox")
    for element in infobox:
        rows = element.find_all('tr')        
        bio = [row.get_text(" ", strip=True) for row in rows]
        for row in bio:
            death_match = re.findall(r'Died.*', row)
            if death_match:
                return
        return bio

#Function to obtain and clean marriage data
def clean_marriage_data(bio):
    clean_marriage_data = []
    marriage_data = []
    for element in bio:
        marriage_match = re.findall(r'Spouse[(s)]*.*', element)
        if(marriage_match):
            marriage_match = re.sub(r"\u200b", "", marriage_match[0])
            marriage_match = re.sub(r"Spouse[(s)]*", "", marriage_match)
            marriage_match = re.sub(r"\[\d\]", "", marriage_match)
            #Wikipedia lists marriage data in a variety of ways: "m." for married, "cp." for civil partnership, etc.
            #All cases are considered here and removed from the string to turn the years into integers.
            marriage_match = re.sub(r"\s*(m\.)\s+|\s*(div\.)\.*\s+|\(|\)|\s*(died)\s+|\s*(cp\.)\.*\s+|\s*(separated)\.*\s+|\s*(divorced )\.*\s+", \
                                    " ", marriage_match)
            marriage_list = marriage_match.split("  ")
            marriage_list = [item.strip() for item in marriage_list]
            for item in marriage_list:
                if item == '':
                    marriage_list.remove(item)
            split_years = re.compile(r'; |, |\/ ').split
            marriage_data = [year for marriage in marriage_list for year in split_years(marriage) if year]
            for item in marriage_data:
                try:
                    clean_marriage_data.append(int(item))
                except:
                    clean_marriage_data.append(item)
            return clean_marriage_data
    return clean_marriage_data

#Function to create a dictionary containing marriage data
#Iterate through this to create a DataFrame
def create_marriage_dict(marriage_data):
    marriage_dict = {}
    if len(marriage_data) == 0:
        pass
    else:
        marriage_count = 1
        currently_married = False
        '''
        Several considerations to be made here given that the way data is included in Wikipedia can vary:
        First case includes the person's name and a married/separated year.
        If an IndexError occurs it either means that there's no second name to be found, or there was
        no separation (currently married). If no second name is found, it means the person married
        their previous partner again. 
        '''
        for i in range(0, len(marriage_data), 3):
            try:
                duration = marriage_data[i+2] - marriage_data[i+1]
                marriage_dict['marriage_' + str(marriage_count) + '_to'] = marriage_data[i]
                marriage_dict['marriage_' + str(marriage_count) + '_duration' ] = duration
                marriage_dict['marriage_' + str(marriage_count) + '_status'] = currently_married
            except IndexError:
                if isinstance(marriage_data[i], int):
                    marriage_dict['marriage_' + str(marriage_count) + '_to'] = \
                    marriage_dict['marriage_' + str(marriage_count - 1) + '_to']
                    try:
                        duration = marriage_data[i+1] - marriage_data[i]
                        marriage_dict['marriage_' + str(marriage_count) + '_duration'] = duration
                        marriage_dict['marriage_' + str(marriage_count) + '_status'] = currently_married
                    except IndexError:
                        currently_married = True
                        marriage_dict['marriage_' + str(marriage_count) + '_duration'] = 2021 - marriage_data[i]
                        marriage_dict['marriage_' + str(marriage_count) + '_status'] = currently_married
                else:
                    currently_married = True
                    marriage_dict['marriage_' + str(marriage_count) + '_to'] = marriage_data[i]
                    marriage_dict['marriage_' + str(marriage_count) + '_duration'] = 2021 - marriage_data[i+1]
                    marriage_dict['marriage_' + str(marriage_count) + '_status'] = currently_married
            marriage_count += 1
    return marriage_dict, marriage_count

#Function to get person's occupation
def get_occupation(bio):
    for element in bio:
        occupation_match = re.findall(r'Occupation[(s)]*.*', element)
        if occupation_match:
            occupation_match = re.sub(r'Occupation[(s)]*', '', occupation_match[0])
            occupation_list = occupation_match.split(",")
            for item in occupation_list:
                item = item.title()
                '''Since we're comparing these occupations' marriage/divorce counts
                We want to make sure they're as uniform as possible, therefore
                singers, musicians, etc. are all "musicians" and people with multiple
                professions will be defaulted to the first one listed on their bio.
                Since politicians do not often show an "occupation" on their Wikipedia page,
                we manually assign their occupation if we find that they're in office.'''
                if item == '':
                    occupation_list.remove(item)
                elif ("Musician" in item) or ("Singer" in item) or ("Rapper" in item) or ("Songwriter" in item):
                    main_occupation = "Musician"
                    break
                elif "Actress" in item:
                    main_occupation = "Actress"
                    break
                elif "Actor" in item:
                    main_occupation = "Actor"
                    break
                elif "Politician" in item:
                    main_occupation = "Politician"
                else:
                    main_occupation = item.strip()
        else:
            occupation_match = re.findall(r'office.*', element)
            if occupation_match:
                main_occupation = "Politician"
    return main_occupation


#Function to create a DF row for this person using previously-created functions
def create_df_entry(person_name):
    df = pd.DataFrame(columns=['name', 'occupation', 'marriage_no', 'partner_name', 'duration_years', \
                            'currently_married', 'partner_occupation'])
    try:
        bio = scrape_bio(person_name)
    except:
        try:
            bio = scrape_bio(person_name + "_(politician)")
        except:
            return
    try:
        marriage_data = clean_marriage_data(bio)
        marriage_dict, marriage_count = create_marriage_dict(marriage_data)
    except:
        return
    try:
        occupation = get_occupation(bio)
    except:
        occupation = "Unknown"
    currently_married = False
    for i in range(1, marriage_count):
        partner_name = marriage_dict.get('marriage_' + str(i) + '_to')
        duration = marriage_dict.get('marriage_' + str(i) + '_duration')
        currently_married = marriage_dict.get('marriage_' + str(i) + '_status')
        partner_occupation = "Unknown"
        try:
            partner_bio = scrape_bio(partner_name)
            partner_occupation = get_occupation(partner_bio)
        except:
            pass
        df = df.append({
            'name': person_name,
            'occupation': occupation,
            'marriage_no': i,
            'partner_name': partner_name,
            'duration_years': duration,
            'currently_married': currently_married,
            'partner_occupation': partner_occupation,
        }, ignore_index=True)
    return df

#Create the DataFrame and populate it
df = pd.DataFrame()
for politician in politicians:
    df = df.append(create_df_entry(politician))
for actor in actors:
    df = df.append(create_df_entry(actor))
for musician in musicians:
    df = df.append(create_df_entry(musician))


#Create CSV file from DF
df.to_csv('marriage_data.csv', index=False)