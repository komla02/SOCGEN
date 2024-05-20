from flask import Flask, request, render_template

app = Flask(__name__)

# Critères d'éligibilité
def verifier_eligibilite(data):
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
    
    montant = data.get('montant', 0)
    echeance = data.get('echeance', 0)
    type_pret = data.get('type_pret', 'NA')
    objet_pret = data.get('objet_pret', 'NA')
    
    # Vérification de l'éligibilité générale
    if objet_pret not in criteres_eligibilite["objets_eligibles"]:
        return "Non éligible pour la garantie ARIZ (objet non éligible)"
    
    if not (criteres_eligibilite["echeance_min"] <= echeance <= criteres_eligibilite["echeance_max"]):
        return "Non éligible pour la garantie ARIZ (échéance non éligible)"
    
    if type_pret not in criteres_eligibilite["types_prets"]:
        return "Non éligible pour la garantie ARIZ (type de prêt non éligible)"
    
    # Vérification de l'éligibilité spécifique (GP ou GI)
    if criteres_eligibilite["montant_min_gp"] <= montant <= criteres_eligibilite["montant_max_gp"]:
        return "Éligible pour la Garantie de Portefeuille"
    elif montant >= criteres_eligibilite["montant_min_gi"]:
        return "Éligible pour la Garantie Individuelle"
    else:
        return "Non éligible pour la garantie ARIZ (montant non éligible)"

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        data = {
            'montant': int(request.form.get('montant', 0)),
            'echeance': int(request.form.get('echeance', 0)),
            'type_pret': request.form.get('type_pret', 'NA'),
            'objet_pret': request.form.get('objet_pret', 'NA')
        }
        resultat = verifier_eligibilite(data)
        return render_template('index.html', resultat=resultat)
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
