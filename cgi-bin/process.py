#!/usr/bin/env python3
import cgi
import dataMap
import re
import ast
import numpy as np

print("Content-Type: text/html\n")

form = cgi.FieldStorage()
text = form.getvalue("description")
text_lower = text.lower()  

pattern_rent = r'\b(?:' + '|'.join(re.escape(term) for term in dataMap.rentalshipMap) + r')\b'
pattern_own = r'\b(?:' + '|'.join(re.escape(term) for term in dataMap.ownershipMap) + r')\b'

matches_rent = [(match.group(), match.start()) for match in re.finditer(pattern_rent, text, re.IGNORECASE)]
matches_own = [(match.group(), match.start()) for match in re.finditer(pattern_own, text, re.IGNORECASE)]

all_matches = [(word, index, "rental") for word, index in matches_rent] + \
              [(word, index, "ownership") for word, index in matches_own]

all_matches.sort(key=lambda x: x[1])  

detected_relationship = None

if not all_matches:

    print("No property type found")

else:

    found_property_types = {}
    for word, property_type in dataMap.propertyMap.items():
        if word.lower() in text_lower:
            found_property_types[word] = property_type

    detected_property = None
    detected_property_position = None

    if len(all_matches) == 1:
        detected_relationship = (all_matches[0][2], all_matches[0][1])

    if found_property_types:

        if detected_relationship is None:
            sorted_types = sorted(found_property_types.keys(), key=lambda w: text_lower.index(w.lower()))
            closest_relationship = None
            closest_position = None
            min_distance = float('inf')

            for word, index, category in all_matches:
                for prop in sorted_types:
                    prop_index = text_lower.index(prop.lower())
                    distance = abs(index - prop_index)
                    
                    if distance < min_distance:
                        min_distance = distance
                        closest_relationship = category
                        closest_position = index

            detected_relationship = (closest_relationship, closest_position) if closest_relationship else (all_matches[0][2], all_matches[0][1])

        if len(found_property_types) > 1:

            sorted_types = sorted(found_property_types.keys(), key=lambda w: text_lower.index(w.lower()))

            detected_relationship_position = detected_relationship[1] 

            search_radius = 50  
            start = max(0, detected_relationship_position - search_radius)
            end = min(len(text_lower), detected_relationship_position + search_radius)
            surrounding_text = text_lower[start:end]

            detected_property = None

            for prop in sorted_types:
                if prop.lower() in surrounding_text:
                    detected_property = found_property_types[prop]
                    detected_property_position = text_lower.index(prop.lower())
                    break
            
            if detected_property is None:

                if detected_relationship[0] == "rental":
                    relationship_keywords = set(k for k in dataMap.rentalshipMap)
                else:
                    relationship_keywords = set(k for k in dataMap.ownershipMap)
                
                for prop in sorted_types:
                   index = text_lower.index(prop.lower())
                
                   start = max(0, index-30)
                   end = index+len(prop)+30
                   surrounding_text = text_lower[start:end]
                   
                   if any(keyword in surrounding_text for keyword in relationship_keywords):
                       detected_property = found_property_types[prop]
                       detected_property_position = index
                       break
                   
            else:
                detected_property = found_property_types[sorted_types[0]]
                detected_property_position = text_lower.find(sorted_types[0].lower())
        else:
            detected_property = next(iter(found_property_types.values()))
            detected_property_position = text_lower.find(next(iter(found_property_types.keys())).lower())

        text_lower = " ".join(word_lower for word_lower in text_lower.split() if word_lower not in found_property_types) # Removing the word from the text

    else:

        import nltk
        from nltk.corpus import wordnet
        
        try:
            wordnet.synsets("test")
        except LookupError:
            nltk.download('wordnet', quiet=True)
        
        property_keys = {word.lower() for word in dataMap.propertyMap.keys()}
        
        for word_lower in (w for w in text_lower.split() if len(w) >= 4):

            for syn in wordnet.synsets(word_lower):
                for lemma in syn.lemmas():
                    synonym = lemma.name().replace("_", " ").lower()

                    if synonym in property_keys:
                        detected_property = synonym
                        detected_property_position = text_lower.index(word_lower)

                        if detected_relationship is None:
                            detected_relationship = (all_matches[0][2], all_matches[0][1])

                        text_lower = text_lower.replace(word_lower, "") # Removing the word from the text

                        break

                if detected_property:
                    break

            if detected_property:
                break

    if not detected_property:

        print("No property found")

    else:

        found_locations = {}
        for location in dataMap.locationMap:
            location_name = location["name"].lower()  
            if location_name in text_lower:
                found_locations[location_name] = text_lower.index(location_name)

        selected_location = {}
        detected_location = []

        if len(found_locations) == 0:

            print("No location found")

        else:

            if len(found_locations) > 1:

                sorted_locations = sorted(found_locations.keys(), key=lambda w: text_lower.index(w))
                
                i = 0
                while i < len(sorted_locations):
                    loc1 = sorted_locations[i]
                    index1 = found_locations[loc1]
                    location_group = [loc1]
                    
                    j = i + 1
                    while j < len(sorted_locations):
                        loc2 = sorted_locations[j]
                        index2 = found_locations[loc2]
                        
                        between_text = text_lower[index1 + len(loc1):index2].strip()

                        if between_text == 'and' or between_text == ',':

                            location_group.append(loc2)
                            index1 = index2
                            loc1 = loc2
                            j += 1  
                        else:
                            break
                    
                    if len(location_group) > 1:
                        selected_location[location_group[0]] = (found_locations[location_group[0]], *location_group[1:])
                    
                    i = j  

                if len(selected_location) > 0:
                    
                    if len(selected_location) > 1:

                        detected_relationship_position = detected_relationship[1] 

                        closest_loc1 = min(
                            selected_location.keys(),
                            key=lambda loc: abs(found_locations[loc]  - detected_relationship_position)
                        )

                        detected_location.append(closest_loc1)
                        detected_location.extend(selected_location[closest_loc1][1:] if len(selected_location[closest_loc1]) > 1 else [])
                        
                    else:
    
                        loc1, loc_values = next(iter(selected_location.items()))
                        detected_location.append(loc1)
                        detected_location.extend(loc_values[1:] if len(loc_values) > 1 else [])

                else:
   
                    for i in range(len(sorted_locations) - 1):
                        loc1, loc2 = sorted_locations[i], sorted_locations[i + 1]
                        index1, index2 = found_locations[loc1], found_locations[loc2]
                        distance = index2 - index1
                        
                        if distance <= 15:
                            between_text = text[index1 + len(loc1) : index2].strip()

                            if any(conj in between_text for conj in dataMap.conjunctionalMap):
                                selected_location[loc1] = (index1, loc2)

                    if len(selected_location) > 1:
                        detected_relationship_position = detected_relationship[1] 

                        closest_loc1 = min(
                            selected_location.keys(),
                            key=lambda loc: abs(found_locations[loc]  - detected_relationship_position)
                        )

                        detected_location.append(closest_loc1)
                        detected_location.append(selected_location[closest_loc1][1])

                    else: 
                        if selected_location:
                            loc1, (index1, loc2) = next(iter(selected_location.items()))  
                            detected_location.append(loc1)  
                            detected_location.append(loc2)

                        else:
                            detected_relationship_position = detected_relationship[1] 

                            closest_location = min(
                                found_locations.keys(),
                                key=lambda loc: abs(found_locations[loc] - detected_relationship_position)
                            )

                            detected_location.append(closest_location)

            else:
                detected_location = list(found_locations.keys()) 

            text_lower = " ".join(word_lower for word_lower in text_lower.split() if word_lower not in found_locations) # Removing the word from the text

            detected_luxury_amenities = []
            for word, luxury_amenity_code in dataMap.luxAmenMap.items():
                word_cleaned = word.strip().lower()
                if word_cleaned in text_lower:
                    
                    detected_luxury_amenities.append(luxury_amenity_code) 

            detected_luxury_amenities = list(dict.fromkeys(detected_luxury_amenities))

            detected_nonluxury_amenities = []
            for word, nonluxury_amenity_code in dataMap.nonluxAmenMap.items():
                word_cleaned = word.strip().lower()
                if word_cleaned in text_lower:

                    detected_nonluxury_amenities.append(nonluxury_amenity_code)
                    
            detected_nonluxury_amenities = list(dict.fromkeys(detected_nonluxury_amenities))

            found_amounts = [
                (
                    m.group(1) if m.group(1) else (m.group(4) if m.group(4) else '*'), 
                    m.group(2) if m.group(2) else '0',  
                    m.group(3) if m.group(3) else 'unit',  
                    m.start()
                )
                for m in re.finditer(
                    r'([\$\€\₹\£\¥]\.?|rs\.?|inr|rupee|rupees|yen|yens|dollars?|pounds?|usd|euro)?\s*'
                    r'(\d+(?:,\d+)*(?:\.\d+)?)\s*'
                    r'(hundred|thousand|thou|lac|lakh|million|billion|crore|mil|k|bhk|bedroom|bedrooms)?\s*'
                    r'([\$\€\₹\£\¥]\.?|rs\.?|inr|rupee|rupees|yen|yens|dollars?|pounds?|usd|euro)?',
                    text_lower
                )
            ]

            if len(found_amounts) == 0:

                print("No Price Found")

            else:
                found_bhk = []

                found_maintenance_amounts = []

                found_carpet_area = []
                found_covered_area = []

                for i in range(len(found_amounts)):
                    amount = list(found_amounts[i]) 

                    amount = list(amount)  
                    amount[0] = amount[0].replace(".", "") 

                    if amount[0].endswith("s") and amount[0] != 'rs':
                        amount[0] = amount[0][:-1]

                    window_size = 30  
                    start_index = max(0, amount[3] - window_size)
                    end_index = min(len(text_lower), amount[3] + window_size)
                    text_window = text_lower[start_index:end_index]
            
                    for key in dataMap.currencyMap.keys():
                        if key == amount[0]:
                            amount[1] = dataMap.currencyMap[key] * int(amount[1])
                            break 

                    for key in dataMap.priceMap.keys():
                        if key in amount[2]:
                            amount[1] = dataMap.priceMap[key] * int(amount[1])
                            break 

                    if amount[2] in ['bhk', 'bedroom', 'bedrooms']:
                        found_bhk.append(amount)

                    if any(keyword in text_window for keyword in dataMap.maintenancePriceMap):
                        found_maintenance_amounts.append(amount)
                    
                    if amount[0] == "*":
                        for keyword in dataMap.areaConversionMap.keys():
                            if keyword in text_window:
                                amount[1] = dataMap.areaConversionMap[keyword] * int(amount[1])
                                if any(keyword.lower() in text_window for keyword in dataMap.carpet_area_keywords):
                                    found_carpet_area.append(amount)
                                else:
                                    found_covered_area.append(amount)
                                break 

                    found_amounts[i] = tuple(amount)
                    
                detected_price = None

                detected_maintenance_amount = None

                detected_land_area = None
                detected_carpet_area = None
                detected_covered_area = None

                detected_bhk = None

                if len(found_bhk) > 0:
                    found_bhk = [tuple(amount) for amount in found_bhk]
                    found_amounts = [amount for amount in found_amounts if tuple(amount) not in found_bhk]

                    closest_bhk = min(found_bhk, key=lambda amount: abs(amount[3] - detected_property_position))

                    detected_bhk = closest_bhk[1]

                if len(found_carpet_area) > 0:
                    found_carpet_area = [tuple(amount) for amount in found_carpet_area]
                    found_amounts = [amount for amount in found_amounts if tuple(amount) not in found_carpet_area]
                    
                    if detected_property in ["Flat", "House_Villa", "Farm House", "Shop_Showroom", "Warehouse_Godown"]:
                        detected_carpet_area = found_carpet_area[0]
                    else:
                        detected_land_area = found_carpet_area[0]

                if len(found_covered_area) > 0:
                    found_covered_area = [tuple(amount) for amount in found_covered_area]
                    found_amounts = [amount for amount in found_amounts if tuple(amount) not in found_covered_area]

                    if detected_property in ["Flat", "House_Villa", "Farm House", "Shop_Showroom", "Warehouse_Godown"]:
                        detected_covered_area = found_covered_area[0]
                    elif detected_land_area is None:
                        detected_land_area = found_covered_area[0]
                    
                if len(found_maintenance_amounts) > 0:
                    found_maintenance_amounts = [tuple(amount) for amount in found_maintenance_amounts]

                    closest_maintenance_amount = min(
                        found_maintenance_amounts, key=lambda amount: abs(amount[3] - detected_property_position)
                    )
                    detected_maintenance_amount = closest_maintenance_amount[1]

                    filtered_amounts = [amount for amount in found_amounts if tuple(amount) not in found_maintenance_amounts]

                    if filtered_amounts:
                        closest_amount = min(filtered_amounts, key=lambda amount: abs(amount[3] - detected_property_position))

                    detected_price = closest_amount[1]

                else:
                    detected_price = found_amounts[1][1]

                detected_origin_ownershipType = next(
                    (key for key in dataMap.ownershipTypeMap.keys() if key.lower() in text_lower), None
                )

                detected_origin_propertyAge = next(
                    (key for key in dataMap.propertyAgeMap.keys() if key.lower() in text_lower), None
                )

                detected_origin_furnishType = next(
                    (key for key in dataMap.furnishMap.keys() if key.lower() in text_lower), None
                )

                import pandas as pd

                formatted_location = [
                    word.upper() if word.lower() == "bhilai" else word.capitalize() for word in detected_location
                ]

                transactionType = "Rent" if detected_relationship[0] == "rental" else "Sale"

                data_frames = []  

                for location in formatted_location:
                    file_path = rf"C:\Users\OJAS\Desktop\NLP\MagicBricksCSV\{transactionType}\{detected_property}\{location}_output.csv"
                    
                    try:
                        df = pd.read_csv(file_path)
                        data_frames.append(df)
                    except FileNotFoundError:
                        print(f"Warning: File not found for location: {location}")

                if data_frames:

                    data = pd.concat(data_frames)
                    total_properties_inLocation = data.shape[0]
                    # print(total_properties_inLocation) 
                    
                    org_filtered_df = data.dropna(subset=["price"])
                    org_filtered_df = org_filtered_df[org_filtered_df["price"].apply(lambda x: str(x).isdigit())]  
                    org_filtered_df["price"] = org_filtered_df["price"].astype(int) 
                    org_filtered_df = org_filtered_df[org_filtered_df["price"].astype(int) <= int(detected_price)]
                    total_properties_priceRelevant = org_filtered_df.shape[0]
                    # print(total_properties_priceRelevant) 

                    filtered_df = org_filtered_df.copy()

                    if detected_carpet_area is not None:

                        filtered_df = filtered_df.reset_index(drop=True)
                        org_filtered_df = org_filtered_df.reset_index(drop=True)

                        filtered_df.loc[:, "carpetArea"] = org_filtered_df["carpetArea"].astype(str).apply(lambda x: re.findall(r'\d+', x)[0] if re.findall(r'\d+', x) else None)
                        filtered_df = filtered_df.dropna(subset=["carpetArea"])
                        filtered_df.loc[:, "carpetArea"] = filtered_df["carpetArea"].astype(int)  
                        filtered_df_final = filtered_df[filtered_df["carpetArea"] >= int(detected_carpet_area[1])]
                        total_properties_carpetAreaRelevant = filtered_df_final.shape[0]
                        # print(total_properties_carpetAreaRelevant) 

                    if detected_covered_area is not None:

                        filtered_df = filtered_df.reset_index(drop=True)
                        org_filtered_df = org_filtered_df.reset_index(drop=True)

                        filtered_df.loc[:, "caSqFt"] = org_filtered_df["caSqFt"].astype(str).apply(lambda x: re.findall(r'\d+', x)[0] if re.findall(r'\d+', x) else None)
                        filtered_df = filtered_df.dropna(subset=["caSqFt"])
                        filtered_df.loc[:, "caSqFt"] = filtered_df["caSqFt"].astype(int)            
                        filtered_df_final = filtered_df[filtered_df["caSqFt"] >= int(detected_covered_area[1])]
                        total_properties_coveredAreaRelevant = filtered_df_final.shape[0]
                        # print(total_properties_coveredAreaRelevant)  

                    if detected_land_area is not None:

                        filtered_df = filtered_df.reset_index(drop=True)
                        org_filtered_df = org_filtered_df.reset_index(drop=True)

                        filtered_df.loc[:, "la"] = org_filtered_df["la"].astype(str).apply(lambda x: re.findall(r'\d+', x)[0] if re.findall(r'\d+', x) else None)
                        filtered_df = filtered_df.dropna(subset=["la"])
                        filtered_df.loc[:, "la"] = filtered_df["la"].astype(int)   
                        filtered_df_final = filtered_df[filtered_df["la"] >= int(detected_land_area[1])]
                        total_properties_landAreaRelevant = filtered_df_final.shape[0]
                        # print(total_properties_landAreaRelevant)  

                    if detected_property in ["Flat", "Office Space", "House_Villa", "Farm House", "Industrial Building", "Plot_Land", "Shop_Showroom", "Warehouse_Godown"]:
                        if detected_origin_ownershipType is not None:
                                                    
                            org_filtered_df = org_filtered_df.reset_index(drop=True)

                            higher_origin_ownershipType = [key for key, value in dataMap.ownershipTypeMap.items() if value >= dataMap.ownershipTypeMap[detected_origin_ownershipType]]
                            filtered_df_final = org_filtered_df[org_filtered_df["OwnershipTypeD"].isin(higher_origin_ownershipType)]
                            total_properties_ownershipTypeRelevant = filtered_df_final.shape[0] 
                            # print(total_properties_ownershipTypeRelevant)                           

                    if detected_property in ["Flat", "Office Space", "House_Villa", "Plot_Land", "Shop_Showroom", "Warehouse_Godown"]:
                        if detected_origin_propertyAge is not None:

                            org_filtered_df = org_filtered_df.reset_index(drop=True)

                            higher_origin_propertyAge = [key for key, value in dataMap.propertyAgeMap.items() if value >= dataMap.propertyAgeMap[detected_origin_propertyAge]]
                            filtered_df_final = org_filtered_df[org_filtered_df["acD"].isin(higher_origin_propertyAge)]
                            total_properties_propertyAgeRelevant = filtered_df_final.shape[0]    
                            # print(total_properties_propertyAgeRelevant)                            

                    if detected_property in ["Flat", "Office Space", "House_Villa", "Farm House", "Industrial Building"]:
                        if detected_origin_furnishType is not None:

                            org_filtered_df = org_filtered_df.reset_index(drop=True)

                            higher_origin_furnishType = [key for key, value in dataMap.furnishMap.items() if value >= dataMap.furnishMap[detected_origin_furnishType]]
                            filtered_df_final = org_filtered_df[org_filtered_df["furnishedD"].isin(higher_origin_furnishType)]
                            total_properties_furnishTypeRelevant = filtered_df_final.shape[0] 
                            # print(total_properties_furnishTypeRelevant)

                    if detected_property in ["Flat", "Office Space", "House_Villa", "Farm House", "Shop_Showroom", "Warehouse_Godown"]:
                        if detected_maintenance_amount is not None:

                            filtered_df = filtered_df.reset_index(drop=True)
                            org_filtered_df = org_filtered_df.reset_index(drop=True)

                            filtered_df.loc[:, "maintenanceCharges"] = org_filtered_df["maintenanceCharges"].astype(str).apply(lambda x: re.findall(r'\d+', x)[0] if re.findall(r'\d+', x) else None)
                            filtered_df = filtered_df.dropna(subset=["maintenanceCharges"])
                            filtered_df.loc[:, "maintenanceCharges"] = filtered_df["maintenanceCharges"].astype(int) 
                            filtered_df_final = filtered_df[filtered_df["maintenanceCharges"] <= int(detected_maintenance_amount)]
                            total_properties_maintenanceAmountRelevant = filtered_df_final.shape[0]
                            # print(total_properties_maintenanceAmountRelevant)

                    if detected_luxury_amenities:

                        org_filtered_df = org_filtered_df.reset_index(drop=True)

                        org_filtered_df.loc[:, "luxAmenMap"] = org_filtered_df["luxAmenMap"].apply(ast.literal_eval)
                        filtered_df_final = org_filtered_df[org_filtered_df["luxAmenMap"].apply(lambda d: any(str(key) in d for key in detected_luxury_amenities))]
                        total_properties_luxuryAmenitiesRelevant = filtered_df_final.shape[0]
                        # print(total_properties_luxuryAmenitiesRelevant)

                    if detected_nonluxury_amenities:

                        org_filtered_df = org_filtered_df.reset_index(drop=True)

                        org_filtered_df.loc[:, "nonluxAmenMap"] = org_filtered_df["nonluxAmenMap"].apply(ast.literal_eval)
                        filtered_df_final = org_filtered_df[org_filtered_df["nonluxAmenMap"].apply(lambda d: any(str(key) in d for key in detected_nonluxury_amenities))]
                        total_properties_nonluxuryAmenitiesRelevant = filtered_df_final.shape[0]
                        # print(total_properties_nonluxuryAmenitiesRelevant)

                    if detected_bhk and detected_property in ["Flat", "House_Villa", "Farm House"]:

                        filtered_df = filtered_df.reset_index(drop=True)
                        org_filtered_df = org_filtered_df.reset_index(drop=True)

                        filtered_df.loc[:, "bedroomD"] = org_filtered_df["bedroomD"].astype(str).apply(lambda x: re.findall(r'\d+', x)[0] if re.findall(r'\d+', x) else None)
                        filtered_df = filtered_df.dropna(subset=["bedroomD"])
                        filtered_df.loc[:, "bedroomD"] = filtered_df["bedroomD"].astype(int)
                        filtered_df_final = filtered_df[filtered_df["bedroomD"] >= int(detected_bhk)]
                        total_properties_bhkRelevant = filtered_df_final.shape[0]
                        # print(total_properties_bhkRelevant)

                weights = {
                    "price": 0.2,
                    "carpetArea": 0.15,
                    "coveredArea": 0.15,
                    "landArea": 0.1,
                    "ownershipType": 0.1,
                    "propertyAge": 0.1,
                    "furnishType": 0.05,
                    "maintenanceAmount": 0.05,
                    "luxuryAmenities": 0.05,
                    "nonluxuryAmenities": 0.05,
                    "bhk": 0.1
                }

                criteria_counts = {
                    "price": total_properties_priceRelevant / total_properties_inLocation if total_properties_inLocation else 0,
                    "carpetArea": total_properties_carpetAreaRelevant / total_properties_priceRelevant if detected_carpet_area else 0,
                    "coveredArea": total_properties_coveredAreaRelevant / total_properties_priceRelevant if detected_covered_area else 0,
                    "landArea": total_properties_landAreaRelevant / total_properties_priceRelevant if detected_land_area else 0,
                    "ownershipType": total_properties_ownershipTypeRelevant / total_properties_priceRelevant if detected_origin_ownershipType else 0,
                    "propertyAge": total_properties_propertyAgeRelevant / total_properties_priceRelevant if detected_origin_propertyAge else 0,
                    "furnishType": total_properties_furnishTypeRelevant / total_properties_priceRelevant if detected_origin_furnishType else 0,
                    "maintenanceAmount": total_properties_maintenanceAmountRelevant / total_properties_priceRelevant if detected_maintenance_amount else 0,
                    "luxuryAmenities": total_properties_luxuryAmenitiesRelevant / total_properties_priceRelevant if detected_luxury_amenities else 0,
                    "nonluxuryAmenities": total_properties_nonluxuryAmenitiesRelevant / total_properties_priceRelevant if detected_nonluxury_amenities else 0,
                    "bhk": total_properties_bhkRelevant / total_properties_priceRelevant if detected_bhk else 0,
                }

                # Compute final uniqueness score
                uniqueness_score = sum(weights[crit] * (1 - criteria_counts[crit]) for crit in criteria_counts)

                final_score = uniqueness_score * 100

                if final_score > 80:
                    rating = "Rare Property"
                elif final_score > 60:
                    rating = "High Value"
                elif final_score > 40:
                    rating = "Moderately Common"
                elif final_score > 20:
                    rating = "Competitive"
                else:
                    rating = "Highly Common"
                    
                print(f"""
                <html>
                <head>
                    <title>Property Submission</title>
                    <style>
                        body {{
                            font-family: Arial, sans-serif;
                            background-color: #f8f9fa;
                            margin: 20px;
                            padding: 20px;
                            border-radius: 10px;
                            box-shadow: 0px 0px 10px rgba(0, 0, 0, 0.1);
                        }}
                        
                        h2 {{
                            color: #007bff;
                            text-align: center;
                        }}
                        
                        p {{
                            font-size: 16px;
                            color: #333;
                            background-color: #fff;
                            padding: 10px;
                            border-radius: 5px;
                            box-shadow: 0px 0px 5px rgba(0, 0, 0, 0.1);
                            margin: 5px 0;
                        }}
                        
                        .container {{
                            max-width: 600px;
                            margin: 0 auto;
                            background: white;
                            padding: 20px;
                            border-radius: 10px;
                            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
                        }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h2>Submitted Property Description</h2>
                        <p>{text}</p>
                        <p>{"Rent" if detected_relationship[0] == "rental" else "Sale"}</p>
                        <p>{detected_property}</p>
                        <p>{detected_location}</p>
                        <p>{detected_luxury_amenities}</p>
                        <p>{detected_nonluxury_amenities}</p>
                        <p>{detected_price}</p>
                        <p>{detected_bhk}</p>
                        <p>{detected_maintenance_amount}</p>
                        <p>{detected_carpet_area[1] if detected_carpet_area else "No carpet area"}</p>
                        <p>{detected_covered_area[1] if detected_covered_area else "No covered area"}</p>
                        <p>{detected_origin_ownershipType}</p>
                        <p>{detected_origin_propertyAge}</p>
                        <p>{detected_origin_furnishType}</p>
                    </div>
                </body>
                </html>
                """)

                print(f"Property Rating: {rating} ({final_score:.2f}%)")
