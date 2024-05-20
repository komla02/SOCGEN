import pandas as pd
from flask import Flask, request, render_template, redirect, url_for
from werkzeug.utils import secure_filename
import os
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

# Critères d'éligibilité et calculs de commission
criteres_eligibilite = {
    "montant_min_gp": 6000000,
    "montant_max_gp": 200000000,
    "montant_min_gi": 200000000,
    "echeance_min": 1,
    "echeance_max": 7,
    "objets_eligibles": ["Financement Treso", "Financement Exploitation"],
    "types_prets": [
        "CLICOM CCT TRESORERIE", "CLIPRO CMT EQUIPEMENT", "CLICOM CMT EQUIPEMENT",
        "CLICOM CMT TRESORERIE", "CLICOM CLT CONSTRUCTION", "CLICOM CMT CONSTRUCTION",
        "CLIPRO CCT EQUIPEMENT", "CLIPRO CLT EQUIPEMENT", "C.M.T. CONSTRUCTION ADMINIST.",
        "CLICOM CMT DIVERS", "CLICOM CCT EQUIPEMENT"
    ]
}

def verifier_eligibilite(row):
    montant = row['Montant du pret']
    echeance = row['Nombre d\'echeance du pret']
    type_pret = row['Type de pret']
    objet_pret = row['Libelle type de pret']
    
    if objet_pret not in criteres_eligibilite["objets_eligibles"]:
        return "Non éligible pour la garantie ARIZ (objet non éligible)"
    
    if not (criteres_eligibilite["echeance_min"] <= echeance <= criteres_eligibilite["echeance_max"]):
        return "Non éligible pour la garantie ARIZ (échéance non éligible)"
    
    if type_pret not in criteres_eligibilite["types_prets"]:
        return "Non éligible pour la garantie ARIZ (type de prêt non éligible)"
    
    if criteres_eligibilite["montant_min_gp"] <= montant <= criteres_eligibilite["montant_max_gp"]:
        return "Éligible pour la Garantie de Portefeuille"
    elif montant >= criteres_eligibilite["montant_min_gi"]:
        return "Éligible pour la Garantie Individuelle"
    else:
        return "Non éligible pour la garantie ARIZ (montant non éligible)"

def calculer_commissions_et_indemnites(row):
    montant = row['Montant du pret']
    date_mise_en_place = row['Date de mise en place']
    date_derniere_echeance = row['Date de derniere echeance']
    
    # Commission d'instruction : 1% du montant du prêt à la date de mise en place
    commission_instruction = montant * 0.01
    
    # Calcul des commissions de sous-participation par semestre (1.7% du montant du prêt par semestre)
    commissions_sous_participation = []
    current_date = date_mise_en_place
    while current_date <= date_derniere_echeance:
        semester = (current_date.month - 1) // 6 + 1
        year = current_date.year
        commission_sous_participation = montant * 0.017
        commissions_sous_participation.append({
            'semestre': semester,
            'année': year,
            'montant': commission_sous_participation
        })
        if semester == 1:
            current_date = current_date.replace(month=7)
        else:
            current_date = current_date.replace(year=year + 1, month=1)
    
    # Indemnité : 50% du montant du prêt en cas de défaut
    indemnite = montant * 0.5
    
    return commission_instruction, commissions_sous_participation, indemnite

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['file']
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            return redirect(url_for('results', filename=filename))
    return render_template('index_com.html')

@app.route('/results/<filename>', methods=['GET'])
def results(filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    df = pd.read_excel(filepath)
    
    df['Date de mise en place'] = pd.to_datetime(df['Date de mise en place'])
    df['Date de derniere echeance'] = pd.to_datetime(df['Date de derniere echeance'])
    
    df['Éligibilité'] = df.apply(verifier_eligibilite, axis=1)
    df['Commission d\'Instruction'], df['Commissions de Sous-Participation'], df['Indemnité'] = zip(*df.apply(calculer_commissions_et_indemnites, axis=1))
    
    # Transformation des commissions de sous-participation en texte pour affichage
    df['Commissions de Sous-Participation'] = df['Commissions de Sous-Participation'].apply(lambda x: '; '.join([f"Semestre {c['semestre']} {c['année']}: {c['montant']:.2f} FCFA" for c in x]))
    
    eligible_clients = df[df['Éligibilité'].str.contains('Éligible')]
    ineligible_clients = df[~df['Éligibilité'].str.contains('Éligible')]
    
    return render_template('results.html', eligible_clients=eligible_clients.to_html(), ineligible_clients=ineligible_clients.to_html())

@app.route('/recap', methods=['GET', 'POST'])
def recap():
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], request.args.get('filename'))
    df = pd.read_excel(filepath)
    
    df['Date de mise en place'] = pd.to_datetime(df['Date de mise en place'])
    df['Date de derniere echeance'] = pd.to_datetime(df['Date de derniere echeance'])
    
    df['Éligibilité'] = df.apply(verifier_eligibilite, axis=1)
    df['Commission d\'Instruction'], df['Commissions de Sous-Participation'], df['Indemnité'] = zip(*df.apply(calculer_commissions_et_indemnites, axis=1))
    
    # Agrégation des commissions par semestre et par année
    recap_commissions = []
    for index, row in df.iterrows():
        for commission in row['Commissions de Sous-Participation']:
            recap_commissions.append({
                'semestre': commission['semestre'],
                'année': commission['année'],
                'montant': commission['montant']
            })
    
    recap_df = pd.DataFrame(recap_commissions)
    recap_aggregated = recap_df.groupby(['année', 'semestre']).sum().reset_index()
    
    return render_template('recap.html', recap_aggregated=recap_aggregated.to_html())

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)

