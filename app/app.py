import streamlit as st
import pandas as pd
import random
from collections import Counter
import altair as alt

if 'product_scores' not in st.session_state:
    st.session_state['product_scores'] = None
if 'all_products' not in st.session_state:
    st.session_state['all_products'] = None
if 'step' not in st.session_state:
    st.session_state['step'] = 'main'
if 'selected_products' not in st.session_state:
    st.session_state['selected_products'] = None
if 'diet_dict' not in st.session_state:
    st.session_state['diet_dict'] = None

@st.cache_data
def load_data(file_path: str):

    with open(file_path, 'r+', encoding='utf-8') as network_data:

       all_lines = network_data.readlines()
       connections_list = []
       
       for index, line in enumerate(all_lines):

          line = line.strip("\n()").lower()
          
          try:
               n1, n2 = line.split(", ")
          except ValueError:
               print(f"Nie udało się podzielić lini {index + 1}")
          else:
               connections_list.append((n1, n2))


    products = [product for _, product in connections_list]
    counted_products = Counter(products)
    more_than_one = [product for (product, counter) in list(counted_products.items()) if counter > 1]
    connections_list = [(diet, product) for diet, product in connections_list if product in more_than_one]

    d = {}

    for diet, product in connections_list:
        d[diet] = d.get(diet, []) + [product]

    return d

# Function to calculate the score for each diet
def calculate_scores(selected_products, diets):

    product_diet_count = {}

    for prod in selected_products:
        for diet, products in diets.items():
            if prod in products:
                product_diet_count.setdefault(prod, []).append(diet)
    
    diet_scores = {diet: 0 for diet in diets}
    for prod, owning_diets in product_diet_count.items():
        weight = 1 / len(owning_diets)
        for diet in owning_diets:
            diet_scores[diet] += weight

    all_sum = sum(diet_scores.values())
    diet_scores = {diet: round(score / all_sum * 100, 2) for diet, score in diet_scores.items()}
    
    return diet_scores

def calculate_product_scores(diets, diet_scorings):

    product_scores = {}
    
    # Create a reverse mapping of products to the number of diets they are in
    for diet, diet_products in diets.items():
        for product in diet_products:

            if product in product_scores:
                product_scores[product] += 1 * (1 / (diet_scorings[diet] + 1e-1))
            else:
                product_scores[product] = 1 * (1 / (diet_scorings[diet] + 1e-1))
            
    for product in product_scores:
        product_scores[product] = round((1.0 / product_scores[product]), 2)
    
    return product_scores

diet_dict = load_data("dieta-produkt.txt")
st.title('Aplikacja rekomendacji diety')

# Multiselect box for user to choose products
all_products = set([item for sublist in diet_dict.values() for item in sublist])
selected_products = st.multiselect('Wybierz przynajmniej 5 produktów:', sorted(list(all_products)))
submit_button = st.button('Zatwierdź')

if submit_button:
    if len(selected_products) >= 5:
        st.session_state['selected_products'] = selected_products
        st.session_state['diet_dict'] = diet_dict
        st.session_state['step'] = 'ask'
    else:
        st.error('Proszę wybrać przynajmniej 5 produktów, aby kontynuować.')
        st.session_state['step'] = 'main'
    
if st.session_state['step'] == 'ask':

    scores = calculate_scores(selected_products, diet_dict)
    recommended_diet = max(scores, key=scores.get)
    st.write(f"Najbardziej odpowiednia dieta dla Ciebie to: **{recommended_diet}**")
    
    # Plotting
    scores_df = pd.DataFrame.from_dict(scores, orient='index', columns=['Dopasowanie (%)'])
    scores_df.sort_values(by='Dopasowanie (%)', ascending=True, inplace=True)
    scores_df.reset_index(inplace=True)
    scores_df.rename(columns={'index': 'Dieta'}, inplace=True)

# Create an Altair chart object
    chart = alt.Chart(scores_df).mark_bar().encode(
        x=alt.X('Dieta:O', sort='-y'), # Sort bars based on the y-values
        y='Dopasowanie (%):Q',
        tooltip=['Dieta', 'Dopasowanie (%)']
    ).properties(
        width=600,
        height=400
    )

    # Display the chart in Streamlit
    st.altair_chart(chart)

    diet_products = set(diet_dict[recommended_diet]) - set(selected_products)
    product_scores = calculate_product_scores(diet_dict, scores)
    recommendations = {product: product_scores[product] for product in diet_products}
    best_5_recommendations = dict(sorted(recommendations.items(), key=lambda item: item[1], reverse=True)[:5])

    product_scores_df = pd.DataFrame.from_dict(best_5_recommendations, orient='index', columns=['Poziom rekomendacji (%)'])
    product_scores_df = product_scores_df.sort_values(by='Poziom rekomendacji (%)', ascending=False)
    product_scores_df['Poziom rekomendacji (%)'] = product_scores_df['Poziom rekomendacji (%)'].round(2).astype(str)
    st.write(f"Oto 5 najbardziej rekomendowanych produktów dla Ciebie, które warto umieścić w swojej diecie:")
    st.table(product_scores_df)

    st.write('Jeśli chcesz sprawdzić rekomendacje dla innych produktów, kliknij poniższy przycisk:')

    if st.button('Sprawdź rekomendacje dla innych produktów'):
        st.session_state['step'] = 'inne_produkty'
        st.session_state['product_scores'] = product_scores
        st.session_state['all_products'] = all_products
        st.session_state['selected_products'] = selected_products

    # st.session_state['step'] = 'main'

if st.session_state['step'] == 'inne_produkty':

    product_scores = st.session_state['product_scores']
    all_products = st.session_state['all_products']
    selected_products = st.session_state['selected_products']

    results = st.multiselect('Sprawdź wyniki dla wybranych produktów:', sorted(list((set(all_products) - set(selected_products)))))
    submit_button2 = st.button('Sprawdź wyniki')

    if submit_button2:
        if len(results) > 0:

            recommendations = {product: product_scores[product] for product in results}
            recommendations_df = pd.DataFrame.from_dict(recommendations, orient='index', columns=['Poziom rekomendacji (%)'])
            recommendations_df = recommendations_df.sort_values(by='Poziom rekomendacji (%)', ascending=False)
            recommendations_df['Poziom rekomendacji (%)'] = recommendations_df['Poziom rekomendacji (%)'].round(2).astype(str)
            st.write(f"Oto poziom rekomendacji dla wybranych produktów:")
            st.table(recommendations_df)
            st.session_state['step'] = 'main'

        else:
            st.error('Proszę wybrać przynajmniej 1 produkt, aby kontynuować.')
