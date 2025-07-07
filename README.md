# Scripts de téléchargement et conversion des cartes marines SHOM

Ce projet contient deux scripts Python permettant de télécharger des tuiles de cartes marines depuis le service WMTS du SHOM (Service Hydrographique et Océanographique de la Marine) et de les convertir au format MBTiles pour utilisation dans des applications de navigation comme OpenCPN.

## Vue d'ensemble

- **`shom_downloader.py`** : Télécharge les tuiles de cartes marines depuis les services SHOM
- **`tiles_to_mbtiles.py`** : Convertit les tuiles téléchargées au format MBTiles

## Prérequis

### Logiciels requis
- Python 3+
- `curl` (installé par défaut sur la plupart des systèmes Linux/macOS)

### Modules Python
Les scripts utilisent uniquement des modules de la bibliothèque standard Python :
- `math`, `os`, `subprocess`, `sys`, `pathlib`
- `sqlite3`, `json`

## Script 1 : shom_downloader.py

### Description
Ce script télécharge automatiquement les tuiles de cartes marines depuis le service WMTS du SHOM pour une zone géographique et des niveaux de zoom spécifiés.

### Configuration par défaut
Le script est configuré pour télécharger la zone couvrant :
- **Latitude** : 47.0° à 50.0° Nord (côtes françaises de la Manche)
- **Longitude** : -5.0° à 2.0° Est (de la Bretagne occidentale à la frontière belge)  
- **Niveaux de zoom** : 8 à 14

### Utilisation

```bash
python3 shom_downloader.py
```

### Personnalisation
Modifiez les constantes en début de script pour ajuster la zone de téléchargement :

```python
# Configuration de la zone géographique
MIN_LAT = 47.0    # Limite sud
MAX_LAT = 50.0    # Limite nord  
MIN_LON = -5.0    # Limite ouest
MAX_LON = 2.0     # Limite est

# Configuration des niveaux de zoom
MIN_ZOOM = 8      # Zoom minimum (vue large)
MAX_ZOOM = 14     # Zoom maximum (détail)
```

### Fonctionnalités

#### Gestion intelligente des téléchargements
- **Reprise automatique** : Les tuiles déjà téléchargées sont automatiquement ignorées
- **Validation** : Vérification que chaque tuile est un fichier PNG valide
- **Gestion d'erreurs** : Retry automatique et nettoyage des fichiers corrompus
- **Timeout** : Protection contre les téléchargements qui traînent (30s par tuile)

#### Organisation des fichiers
```
shom_tiles_complete/
├── 8/           # Niveau de zoom 8
│   ├── 127/     # Colonne X
│   │   ├── 89.png
│   │   └── 90.png
│   └── 128/
├── 9/           # Niveau de zoom 9
└── ...
```

#### Informations affichées
- Progression du téléchargement par niveau de zoom
- Statistiques : tuiles téléchargées, ignorées, échouées
- Taux de réussite global
- Estimation du nombre total de tuiles

### Exemple de sortie
```
Downloading SHOM tiles for area: 47.0,-5.0 to 50.0,2.0
Zoom levels: 8 to 14

Processing zoom level 8...
Tile range for zoom 8: X(122-135) Y(85-95)
Expected tiles for this zoom level: 154
  Progress: Downloaded 100, Failed 0
Zoom 8 complete: 154 downloaded, 0 failed

Final results:
  Total expected: 15840
  Downloaded: 15621
  Skipped (existed): 0
  Failed: 219
  Success rate: 98.6%
```
> Il peut être normal selon les zones d'avoir un taux d'échec de téléchargement élevé (50% autour des côtes bretonnes).

## Script 2 : tiles_to_mbtiles.py

### Description
Ce script convertit la structure de répertoires de tuiles téléchargées en un fichier MBTiles, format standard pour les applications de cartographie.

### Utilisation

```bash
python3 tiles_to_mbtiles.py
```

### Configuration
Modifiez les constantes si nécessaire :

```python
TILES_ROOT = "shom_tiles_complete"    # Répertoire source des tuiles
MBTILES_FILE = "shom_marine_charts.mbtiles"  # Fichier de sortie
```

### Fonctionnalités

#### Analyse automatique
- **Détection automatique** des niveaux de zoom disponibles
- **Calcul des limites géographiques** basé sur les tuiles présentes
- **Statistiques complètes** sur le contenu

#### Format MBTiles
Le fichier généré respecte la spécification MBTiles 1.3 :
- Base de données SQLite avec tables `tiles` et `metadata`
- Coordonnées converties au schéma TMS (Tile Map Service)
- Métadonnées complètes incluant attribution, limites, etc.

#### Métadonnées incluses
- Nom, description et attribution SHOM
- Limites géographiques précises
- Niveaux de zoom min/max
- Point central calculé
- Statistiques des couches

### Exemple de sortie
```
Analyzing tiles in shom_tiles_complete...
Found 7 zoom levels:
  Zoom 8: 154 tiles (X: 122-135, Y: 85-95)
  Zoom 9: 616 tiles (X: 245-271, Y: 170-191)
  Zoom 10: 2464 tiles (X: 490-543, Y: 340-383)
  ...
Geographic bounds: 47.0000,-5.0000 to 50.0000,2.0000

Processing zoom level 8...
Processing zoom level 9...
...

MBTiles creation complete!
  File: shom_marine_charts.mbtiles
  Tiles inserted: 15621/15840
  Zoom levels: 8-14
  File size: 245.7 MB

Ready to use with OpenCPN: shom_marine_charts.mbtiles
```

## Utilisation avec OpenCPN

### Installation
1. Copiez le fichier `.mbtiles` dans le répertoire des cartes d'OpenCPN
2. Redémarrez OpenCPN ou actualisez la liste des cartes
3. Les cartes SHOM apparaîtront dans la liste des cartes disponibles

### Répertoires OpenCPN typiques
- **Linux** : `~/.opencpn/charts/`
- **Windows** : `C:\ProgramData\opencpn\charts\`
- **macOS** : `~/Library/Application Support/OpenCPN/charts/`

## Informations techniques

### Source des données
- **Service** : WMTS SHOM (services.data.shom.fr)
- **Couche** : RASTER_MARINE_3857_WMTS
- **Projection** : Web Mercator (EPSG:3857)
- **Format** : PNG

### Structure des URLs WMTS
```
https://services.data.shom.fr/clevisu/wmts?
layer=RASTER_MARINE_3857_WMTS&
style=normal&
tilematrixset=3857&
Service=WMTS&
Request=GetTile&
Version=1.0.0&
Format=image%2Fpng&
TileMatrix={z}&
TileCol={x}&
TileRow={y}
```

### Calculs de géoréférencement
Les scripts utilisent les formules standard de conversion Web Mercator :
- Conversion degré → tuile : projection sphérique Mercator
- Gestion de la coordonnée Y inversée entre WMTS et TMS

## Limites et considérations

### Légales
- Respectez les conditions d'utilisation du SHOM
- Usage personnel et non commercial recommandé
- Attribution obligatoire : "SHOM - Service Hydrographique et Océanographique de la Marine"

### Techniques
- **Bande passante** : Le téléchargement peut être long (plusieurs Go pour les grandes zones)
- **Stockage** : Prévoyez suffisamment d'espace disque
- **Politesse** : Le script respecte le serveur avec des en-têtes HTTP appropriés

### Limitations des données
- Couverture limitée aux eaux françaises et proches
- Mise à jour des cartes selon le calendrier SHOM
- Qualité variable selon les zones

## Dépannage

### Erreurs communes

#### "Failed to download tile"
- Vérifiez votre connexion internet
- Le serveur SHOM peut être temporairement indisponible
- Certaines tuiles peuvent ne pas exister pour certaines zones

#### "No tiles found"
- Vérifiez le répertoire source dans `tiles_to_mbtiles.py`
- Assurez-vous que le téléchargement s'est correctement déroulé

#### "Database locked" 
- Fermez toute application utilisant le fichier MBTiles
- Supprimez le fichier `.mbtiles` existant avant de relancer

### Optimisation
- Ajustez les niveaux de zoom selon vos besoins (zoom élevé = plus de tuiles)
- Utilisez des zones géographiques plus petites pour des tests
- Surveillez l'espace disque disponible

## Licence et attribution

Ces scripts sont fournis à des fins éducatives et de navigation personnelle.

**Attribution obligatoire pour les cartes** :
> SHOM - Service Hydrographique et Océanographique de la Marine

**Liens utiles** :
- [SHOM - data.shom.fr](https://data.shom.fr)
- [Spécification MBTiles](https://github.com/mapbox/mbtiles-spec)
- [OpenCPN](https://opencpn.org)
