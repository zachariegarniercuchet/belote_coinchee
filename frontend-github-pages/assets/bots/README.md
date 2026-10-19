# Portraits des bots

12 illustrations originales générées avec l'outil intégré `image_gen`.
Direction : portraits cartoon expressifs pour un jeu de cartes, contours nets,
couleurs chaudes et accessoires lisibles en miniature. Ce ne sont pas des
personnages ni des images repris de Chess.com.

- West : Buck, Daisy, Hank, Bonnie ; chapeaux de cowboy et foulards.
- Bohème : Basile, Alma, Marceau, Suzon ; bonnets et lunettes.
- de Belote : Charles, Aliénor, Octave, Apolline ; hauts-de-forme et parures.

Les versions d'une famille partagent ses quatre portraits. Les fichiers PNG
sont les sorties originales ; les prompts finaux et leur mode de génération
sont conservés dans [prompts.json](prompts.json). Charles a servi de référence
de style pour les onze autres portraits.

Flask sert uniquement les images référencées dans le catalogue, via
`/assets/bots/<fichier>`, avec un cache de 24 h. Les README/prompts ne sont pas
servis par cette route. GitHub Pages dispose directement des mêmes fichiers.
L'interface charge les portraits à la demande et arrondit légèrement les coins
(4 px), sans les recadrer en cercle.
