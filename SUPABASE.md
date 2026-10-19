# Comptes optionnels (Supabase)

L'application se joue **sans aucun compte** : c'est le mode par défaut, il ne
change jamais par rapport à aujourd'hui. Un joueur qui le souhaite peut
cependant se connecter ou créer un compte (email + mot de passe) pour que ses
parties terminées soient conservées et retrouvées depuis n'importe quel
appareil.

- **Invité** : il ouvre l'app, entre son prénom, joue. Aucun appel Supabase,
  aucun stockage, l'application fonctionne même si Supabase est en panne.
- **Connecté** : bouton **Connexion** sur l'écran d'accueil, puis **Mes
  parties** (historique) et **Déconnexion**. Le prénom est pré-rempli.

Fichiers concernés : `auth.js` (identique dans les deux frontends),
`index.html`, `style.css`, `server.py`, `game_session.py`, `supabase/setup.sql`.

---

## 1. Récupérer les clés du projet

Dans Supabase : **Project Settings → API**

- **Project URL** → variable `SUPABASE_URL`
- **anon / publishable key** → variable `SUPABASE_ANON_KEY`

Ces deux valeurs sont **publiques** : elles peuvent figurer dans le code du
navigateur. La clé `service_role` (secrète) ne doit **jamais** quitter la
console Supabase.

Puis dans **Authentication → Sign In / Providers** :

- **Email** : activé (c'est le cas par défaut).
- **Confirm email** :
  - *activé* (recommandé en production) : après l'inscription, un lien de
    confirmation arrive par email. L'interface affiche alors
    « Presque ! Ouvre le lien de confirmation… » puis bascule sur Connexion.
  - *désactivé* (choix actuel du projet, le 19 octobre 2026) : l'inscription
    connecte directement, sans lien email — plus fluide, mais n'importe qui
    peut déclarer une adresse qu'il ne possède pas.

> **Limite d'emails du service intégré** : le SMTP fourni par Supabase
> (plan gratuit) n'envoie que quelques messages par heure ; au-delà,
> l'inscription affiche « Trop d'emails envoyés récemment : réessaie dans
> quelques minutes ». Pour une vraie utilisation à plusieurs, brancher un SMTP
> gratuit (**Authentication → SMTP Settings** : Resend, Brevo, Mailgun, SendGrid
> — 30 secondes de réglage) : confirmations, mots de passe oubliés et
> invitations n'auront plus cette limite basse.

Dans **Authentication → URL configuration** :

- **Site URL** : l'adresse principale de l'app (ex.
  `https://belote-coinchee.onrender.com`).
- **Redirect URLs** : ajouter **chaque** origine qui doit pouvoir recevoir les
  liens de confirmation et de mot de passe oublié :
  `https://belote-coinchee.onrender.com` et
  `https://zachariegarniercuchet.github.io` (sans chemin).
  Sans cela, les liens email sont refusés.

## 2. Créer la table d'historique

**SQL Editor → New query** → coller le contenu de `supabase/setup.sql` →
**Run**. Une seule fois.

Ce script crée `game_history` (une ligne par partie terminée et par compte)
avec les politiques **RLS** : chacun ne lit et n'écrit que ses propres lignes.

## 3. Brancher le backend Render

Dans Render → le service → **Environment**, ajouter :

| Variable | Valeur |
| --- | --- |
| `SUPABASE_URL` | `https://<votre-projet>.supabase.co` |
| `SUPABASE_ANON_KEY` | la clé anon du projet |

Ces deux clés sont déjà déclarées (vides) dans `render.yaml` : il suffit de
les renseigner dans le tableau de bord, puis de redéployer. Le serveur les
injecte dans la page (`window.BELOTE_SUPABASE`) ; sans elles, la page reste
exactement en mode invité.

## 4. Brancher la copie GitHub Pages (si elle est utilisée)

Dans `frontend-github-pages/index.html`, compléter le bloc de configuration :

```js
window.BELOTE_SUPABASE = {
  url: "https://<votre-projet>.supabase.co",
  anonKey: "votre-cle-anon"
};
```

Laisser `""` partout conserve le mode invité pur.

> Point d'attention connu : les requêtes HTTP de cette copie (QR code, info de
> salon) sont relatives à l'origine du frontend. Seul Socket.IO utilise
> `window.BELOTE_BACKEND_URL`. Avec des origines différentes, Supabase reste
> indépendant de ce réglage, mais les deux autres types de requêtes doivent
> être vérifiés.

## 5. Tester en local

```powershell
$env:SUPABASE_URL = "https://<votre-projet>.supabase.co"
$env:SUPABASE_ANON_KEY = "votre-cle-anon"
.\.venv\Scripts\python.exe -B server.py
```

Ouvrir `http://localhost:5000` : le bandeau **Invité · aucun compte requis** et
le bouton **Connexion** apparaissent sous le logo. Penser à ajouter
`http://localhost:5000` aux *Redirect URLs* de Supabase si l'on veut tester la
confirmation par email en local.

Vérifications automatisées :

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_supabase_config.py
node --check auth.js
```

## Ce qui est enregistré

| | Invité | Connecté |
| --- | --- | --- |
| Jouer, créer/rejoindre un salon | oui | oui |
| Prénom mémorisé d'une visite à l'autre | non | oui (et réutilisé comme prénom de jeu) |
| Historique et scores des parties terminées | non | oui — bouton **Mes parties** |
| Compte consultable depuis un autre appareil | — | oui |

Une ligne est écrite à la fin de chaque partie (`game_id` unique par partie,
anti-doublon) : date, salon, score cible, nombre de donnes, scores des équipes
A/B, vainqueur, siège et équipe du joueur, prénoms des quatre joueurs.

## Sécurité

- **Aucun mot de passe** n'est stocké par l'application : le hachage est fait
  par Supabase (bcrypt).
- La clé `anon` est publique par conception ; la protection vient des
  politiques RLS définies dans `supabase/setup.sql`. Une requête forcée depuis
  la console ne renvoie que les lignes de l'utilisateur connecté.
- Le serveur de jeu (`server.py`) n'a **aucune** clé Supabase et n'accède
  jamais à la base : il se contente de diffuser une clé publique. L'inscription
  est ouverte à tous (pas de liste d'invitation).
- Le jeu reste jouable si Supabase est injoignable : `auth.js` retombe en mode
  invité et trace simplement l'erreur dans la console.

## Ajouter « Continuer avec Google » plus tard

Rien à prévoir dans la base : seule l'UI manque. Étapes :

1. **Google Cloud Console → APIs & Services → Credentials → Create
   credentials → OAuth client ID → Web application**, avec comme *Authorized
   redirect URI* : `https://<ref-du-projet>.supabase.co/auth/v1/callback`
   (affiché par Supabase lui-même dans le champ du fournisseur).
2. **Supabase → Authentication → Sign In / Providers → Google** : coller le
   *Client ID* et le *Client Secret*, puis **Save**.
3. Vérifier que l'URL de l'app figure bien dans les **Redirect URLs**.
4. Côté interface, un bouton dans `auth.js` (et son équivalent dans les deux
   `index.html`) appelle :

   ```js
   await client.auth.signInWithOAuth({
     provider: "google",
     options: { redirectTo: window.location.origin }
   });
   ```

   La session ainsi obtenue se comporte exactement comme une session email :
   historique, prénom et déconnexion fonctionnent sans autre changement.

## Dépannage

| Message / symptôme | Cause |
| --- | --- |
| Aucun bouton **Connexion** | Variables non renseignées (mode invité voulu), ou `auth.js` absent de la page. |
| « Impossible de joindre le service de comptes » | Mauvaise `SUPABASE_URL`, clé invalide, ou connexion réseau. |
| « Trop d'emails envoyés récemment » | Limite horaire du SMTP intégré à Supabase : brancher un SMTP (voir étape 1) ou réessayer plus tard. |
| « Cette adresse email n'est pas valide » | Format incorrect, ou domaine sans enregistrement MX (un `.test` ou une adresse fictive est refusée à l'envoi). |
| « Historique non installé : lance supabase/setup.sql » | Le SQL n'a pas été exécuté, ou dans un autre projet. |
| « Email non confirmé » | Confirmation activée : cliquer sur le lien reçu. Voir **Authentication → Logs** si le mail n'arrive pas. |
| Lien de confirmation / réinitialisation refusé | Origine absente des **Redirect URLs** (étape 1). |
| Aucune ligne dans **Mes parties** | Le joueur était invité, ou la partie n'est pas terminée (une ligne est écrite à la fin de la partie uniquement). |
