# Genetic Algorithm for Smart TV Scheduling

## Përshkrimi i problemit

Smart TV Scheduling in Public Venues është një problem optimizimi ku sistemi duhet të ndërtojë një orar transmetimi për një ekran të vetëm në një hapësirë publike, duke zgjedhur programe nga disa kanale televizive. Çdo kanal ka një listë programesh me kohë fikse fillimi dhe mbarimi, zhanër dhe pikë popullariteti.

Qëllimi është të gjendet një schedule që maksimizon rezultatin total, duke respektuar kufizime të rëndësishme si mos-mbivendosja e programeve, kohëzgjatja minimale e transmetimit, kufizimet e priority blocks, kufizimi i programeve të njëpasnjëshme me të njëjtin zhanër dhe penalizimet për ndërrim kanali apo transmetime parciale.

## Qëllimi i zgjidhjes

Zgjidhja e implementuar përdor një qasje hibride:

```text
Zgjidhje deterministike fillestare
        +
Algoritëm gjenetik për përmirësim
```
Fillimisht, algoritmi deterministik ndërton një zgjidhje fillestare valide. Kjo zgjidhje përdoret si seed solution për algoritmin gjenetik. Pastaj GA krijon variante të ndryshme të kësaj zgjidhjeje përmes operatorëve të mutacionit dhe crossover-it, i riparon ato nëse shkelin kufizime, i vlerëson me funksionin objektiv dhe gradualisht ruan zgjidhjet më të mira.


### Rrjedha e përgjithshme e algoritmit

Procesi kryesor është:
```text
input.json
   ↓
ndërtimi i segmenteve kandidate
   ↓
filtrimi i segmenteve më të mira
   ↓
algoritmi deterministik gjeneron zgjidhjen fillestare
   ↓
krijohet popullata fillestare për GA
   ↓
popullata evoluon me selection, crossover, mutation, repair dhe fitness evaluation
   ↓
ruhet zgjidhja më e mirë
   ↓
procesi përsëritet disa herë
   ↓
kthehet rezultati më i mirë final
```
Për çdo instancë, algoritmi mund të ekzekutohet disa herë me seed të ndryshëm. Në fund, nga të gjitha ekzekutimet merret rezultati me score më të lartë.

### Konceptimi i algoritmit gjenetik

Në këtë zgjidhje, një individ përfaqëson një schedule kandidat. Një schedule përbëhet nga segmente të programeve të zgjedhura:
```text
(program_id, channel_id, start, end)
```
Popullata është një grup schedules. Fillimisht, popullata krijohet nga zgjidhja deterministike dhe nga variante të saj. Gjatë evolucionit, individët më të mirë zgjidhen si prindër, kombinohen me crossover, ndryshohen me mutation dhe pastaj riparohen për të respektuar kufizimet e problemit.

#### Si evoluon popullata

Në çdo gjeneratë ndodhin këto hapa:

- Popullata renditet sipas score-it
- Individët më të mirë ruhen direkt përmes elitizmit
- Zgjidhen prindër përmes tournament selection
- Nga dy prindër krijohet një child përmes crossover
- Child mund të ndryshohet përmes mutation
- Child kalon në repair për t'u bërë valid
- Llogaritet score-i i child-it
- Popullata e re ndërtohet me individët më të mirë dhe children e rinj
- Nëse nuk ka përmirësim për disa gjenerata, aplikohet mutacion më i fortë për të shmangur ngecjen në local optimum

Ky proces vazhdon deri sa të përfundojë limiti kohor i ekzekutimit.

### Parametrat kryesorë të algoritmit

| Parametri | Përshkrimi |
|-----------|----------|
| runs | Numri i ekzekutimeve të pavarura për një instancë. Çdo run përdor seed të ndryshëm. |
| time_limit | Koha maksimale e evolucionit për një run. |
| population_size | Numri i individëve në popullatë. |
| elite_count | Numri i individëve më të mirë që kalojnë direkt në gjeneratën tjetër. |
| crossover_rate | Probabiliteti që dy prindër të kombinohen me crossover. |
| mutation_rate | Probabiliteti që një child të ndryshohet me mutation. |
| top_k | Numri maksimal i segmenteve më të mira që mbahen për çdo program. |
| seed | Vlera fillestare për randomizim. |
| allow_program_revisit | Tregon nëse i njëjti program lejohet të përdoret më shumë se një herë. |
| revisit_penalty | Penalizimi nëse një program përsëritet, kur përsëritja lejohet. |

## Operatorët e përdorur

### 1. Selection

Përdoret tournament selection.

Ky operator zgjedh disa individë në mënyrë të rastësishme nga popullata dhe prej tyre merr atë me score më të lartë. Ky individ përdoret si prind për crossover.

Qëllimi i selection është që individët më të mirë të kenë më shumë mundësi të kontribuojnë në gjeneratat e ardhshme.

### 2. Crossover

Janë përdorur dy operatorë crossover.

#### Time-cut crossover

Ky operator zgjedh një pikë kohore dhe krijon një child duke marrë pjesën para asaj kohe nga një prind dhe pjesën pas asaj kohe nga prindi tjetër.

Kjo është e përshtatshme për këtë problem sepse schedule-i është i varur drejtpërdrejt nga koha.

#### Block-mix crossover

Ky operator zgjedh një interval kohor dhe kombinon një bllok segmentesh nga një prind me segmentet jashtë atij blloku nga prindi tjetër.

Qëllimi është të ruhet një pjesë e mirë e schedule-it nga një prind, ndërsa pjesa tjetër merret nga prindi tjetër.

### 3. Mutation

Janë përdorur pesë operatorë mutacioni.

#### Replace segment mutation

Zëvendëson një segment ekzistues me një alternativë tjetër nga candidate pool. Alternativa zgjidhet nga segmente që janë afër në kohë me segmentin aktual.

#### Delete weak mutation

Heq segmentin që ka kontributin më të dobët në score. Ky operator përdor marginal contribution për të kuptuar sa ndikon secili segment në rezultatin total.

#### Insert gap mutation

Gjen një hapësirë bosh në schedule dhe tenton të fusë një program të ri që përshtatet brenda atij intervali.

#### Expand boundary mutation

Zgjeron kufijtë e një segmenti parcial, nëse ekziston një version më i gjatë i të njëjtit program që mbetet valid. Ky operator mund të ulë penalizimet për transmetime parciale.

#### Block rebuild mutation

Heq një pjesë të schedule-it dhe e rindërton duke futur kandidatë të rinj. Ky operator ndihmon në eksplorim më të fortë të hapësirës së zgjidhjeve.

### 4. Repair

Repair është një pjesë shumë e rëndësishme e zgjidhjes. Pas crossover-it ose mutation-it, një child mund të ketë probleme si overlap, shkelje të priority blocks ose tejkalim të kufirit të zhanrit të njëpasnjëshëm.

Repair bën këto veprime:

- Heq segmente invalid
- Largon mbivendosjet
- Ruan segmentet me vlerë më të lartë
- Heq përdorimet e dyfishta të të njëjtit program
- Rregullon sekuencat me shumë programe të njëpasnjëshme të të njëjtit zhanër
- Tenton të mbushë gap-et kur kjo e rrit score-in
- E kthen schedule-in në formë valide

### 5. Fitness evaluation

Çdo individ vlerësohet me funksionin objektiv:

```
score = program_score + bonus - switch_penalty * switches - termination_penalty * partials
```

Kjo do të thotë se një schedule është më i mirë nëse:

- Ka programe me score më të lartë
- Fiton më shumë bonus nga time preferences
- Ka më pak ndërrime kanalesh
- Ka më pak transmetime parciale
- Respekton të gjitha kufizimet

### 6. Elitism

Elitizmi ruan individët më të mirë të popullatës dhe i kalon direkt në gjeneratën tjetër pa i ndryshuar.

Kjo siguron që zgjidhjet më të mira të mos humben gjatë crossover-it dhe mutation-it.

## Ekzekutimi për shumë instanca

Rezultatet e algoritmit gjenetik ruhen në folderin:

`results_ga/`

Për çdo instancë krijohet një file output me schedule-in më të mirë të gjetur nga GA.

Gjithashtu, rezultatet përmbledhëse ruhen në:

`tables/results_ga_summary2.csv`

## Rezultatet eksperimentale

