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

| instance | execution | config_id | score | feasible | deterministic_seed_score | ga_score | switches | partials | bonus | program_score | revisits | normalized_length | top_k | population_size | elite_count | seed | allow_program_revisit | revisit_penalty | output_file | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| australia_iptv | 1 | C01 | 4886 | True | 4883 | 4886 | 45 | 3 | 945 | 4451 | 0 | 53 | 8 | 24 | 2 | 1051 | False | 25 | `results_ga\australia_iptv_ga_exec_01_C01.json` |  |
| australia_iptv | 2 | C02 | 4888 | True | 4883 | 4888 | 46 | 3 | 945 | 4463 | 0 | 53 | 10 | 24 | 2 | 2060 | False | 25 | `results_ga\australia_iptv_ga_exec_02_C02.json` |  |
| australia_iptv | 3 | C03 | 4886 | True | 4883 | 4886 | 45 | 3 | 945 | 4451 | 0 | 53 | 12 | 24 | 2 | 3069 | False | 25 | `results_ga\australia_iptv_ga_exec_03_C03.json` |  |
| australia_iptv | 4 | C04 | 4883 | True | 4883 | 4883 | 45 | 3 | 945 | 4448 | 0 | 53 | 8 | 32 | 2 | 4078 | False | 25 | `results_ga\australia_iptv_ga_exec_04_C04.json` |  |
| australia_iptv | 5 | C05 | 4883 | True | 4883 | 4883 | 45 | 3 | 945 | 4448 | 0 | 53 | 10 | 32 | 2 | 5087 | False | 25 | `results_ga\australia_iptv_ga_exec_05_C05.json` |  |
| australia_iptv | 6 | C06 | 4883 | True | 4883 | 4883 | 45 | 3 | 945 | 4448 | 0 | 53 | 12 | 32 | 2 | 6096 | False | 25 | `results_ga\australia_iptv_ga_exec_06_C06.json` |  |
| australia_iptv | 7 | C07 | 4883 | True | 4883 | 4883 | 45 | 3 | 945 | 4448 | 0 | 53 | 8 | 40 | 3 | 7105 | False | 25 | `results_ga\australia_iptv_ga_exec_07_C07.json` |  |
| australia_iptv | 8 | C08 | 4892 | True | 4883 | 4892 | 46 | 3 | 945 | 4467 | 0 | 53 | 10 | 40 | 3 | 8114 | False | 25 | `results_ga\australia_iptv_ga_exec_08_C08.json` |  |
| australia_iptv | 9 | C09 | 4897 | True | 4883 | 4897 | 45 | 3 | 1002 | 4405 | 0 | 52 | 12 | 40 | 3 | 9123 | False | 25 | `results_ga\australia_iptv_ga_exec_09_C09.json` |  |
| australia_iptv | 10 | C10 | 4886 | True | 4883 | 4886 | 45 | 3 | 945 | 4451 | 0 | 53 | 15 | 40 | 3 | 10132 | False | 25 | `results_ga\australia_iptv_ga_exec_10_C10.json` |  |
| canada_pw | 1 | C01 | 5670 | True | 5663 | 5670 | 45 | 2 | 796 | 5364 | 0 | 63 | 8 | 24 | 2 | 1051 | False | 25 | `results_ga\canada_pw_ga_exec_01_C01.json` |  |
| canada_pw | 2 | C02 | 5670 | True | 5663 | 5670 | 45 | 2 | 796 | 5364 | 0 | 63 | 10 | 24 | 2 | 2060 | False | 25 | `results_ga\canada_pw_ga_exec_02_C02.json` |  |
| canada_pw | 3 | C03 | 5671 | True | 5663 | 5671 | 45 | 2 | 796 | 5365 | 0 | 63 | 12 | 24 | 2 | 3069 | False | 25 | `results_ga\canada_pw_ga_exec_03_C03.json` |  |
| canada_pw | 4 | C04 | 5671 | True | 5663 | 5671 | 45 | 2 | 796 | 5365 | 0 | 63 | 8 | 32 | 2 | 4078 | False | 25 | `results_ga\canada_pw_ga_exec_04_C04.json` |  |
| canada_pw | 5 | C05 | 5665 | True | 5663 | 5665 | 45 | 2 | 796 | 5359 | 0 | 63 | 10 | 32 | 2 | 5087 | False | 25 | `results_ga\canada_pw_ga_exec_05_C05.json` |  |
| canada_pw | 6 | C06 | 5671 | True | 5663 | 5671 | 45 | 2 | 796 | 5365 | 0 | 63 | 12 | 32 | 2 | 6096 | False | 25 | `results_ga\canada_pw_ga_exec_06_C06.json` |  |
| canada_pw | 7 | C07 | 5671 | True | 5663 | 5671 | 45 | 2 | 796 | 5365 | 0 | 63 | 8 | 40 | 3 | 7105 | False | 25 | `results_ga\canada_pw_ga_exec_07_C07.json` |  |
| canada_pw | 8 | C08 | 5671 | True | 5663 | 5671 | 45 | 2 | 796 | 5365 | 0 | 63 | 10 | 40 | 3 | 8114 | False | 25 | `results_ga\canada_pw_ga_exec_08_C08.json` |  |
| canada_pw | 9 | C09 | 5663 | True | 5663 | 5663 | 44 | 2 | 796 | 5347 | 0 | 63 | 12 | 40 | 3 | 9123 | False | 25 | `results_ga\canada_pw_ga_exec_09_C09.json` |  |
| canada_pw | 10 | C10 | 5663 | True | 5663 | 5663 | 44 | 2 | 796 | 5347 | 0 | 63 | 15 | 40 | 3 | 10132 | False | 25 | `results_ga\canada_pw_ga_exec_10_C10.json` |  |
| china_pw | 1 | C01 | 3066 | True | 3016 | 3066 | 31 | 14 | 567 | 3089 | 0 | 43 | 8 | 24 | 2 | 1051 | False | 25 | `results_ga\china_pw_ga_exec_01_C01.json` |  |
| china_pw | 2 | C02 | 3116 | True | 3016 | 3116 | 32 | 16 | 522 | 3234 | 0 | 45 | 10 | 24 | 2 | 2060 | False | 25 | `results_ga\china_pw_ga_exec_02_C02.json` |  |
| china_pw | 3 | C03 | 3075 | True | 3016 | 3075 | 30 | 14 | 567 | 3088 | 0 | 43 | 12 | 24 | 2 | 3069 | False | 25 | `results_ga\china_pw_ga_exec_03_C03.json` |  |
| china_pw | 4 | C04 | 3016 | True | 3016 | 3016 | 29 | 15 | 518 | 3088 | 0 | 43 | 8 | 32 | 2 | 4078 | False | 25 | `results_ga\china_pw_ga_exec_04_C04.json` |  |
| china_pw | 5 | C05 | 3016 | True | 3016 | 3016 | 29 | 15 | 518 | 3088 | 0 | 43 | 10 | 32 | 2 | 5087 | False | 25 | `results_ga\china_pw_ga_exec_05_C05.json` |  |
| china_pw | 6 | C06 | 3075 | True | 3016 | 3075 | 30 | 14 | 567 | 3088 | 0 | 43 | 12 | 32 | 2 | 6096 | False | 25 | `results_ga\china_pw_ga_exec_06_C06.json` |  |
| china_pw | 7 | C07 | 3065 | True | 3016 | 3065 | 31 | 14 | 567 | 3088 | 0 | 43 | 8 | 40 | 3 | 7105 | False | 25 | `results_ga\china_pw_ga_exec_07_C07.json` |  |
| china_pw | 8 | C08 | 3075 | True | 3016 | 3075 | 30 | 14 | 567 | 3088 | 0 | 43 | 10 | 40 | 3 | 8114 | False | 25 | `results_ga\china_pw_ga_exec_08_C08.json` |  |
| china_pw | 9 | C09 | 3024 | True | 3016 | 3024 | 30 | 13 | 567 | 3017 | 0 | 42 | 12 | 40 | 3 | 9123 | False | 25 | `results_ga\china_pw_ga_exec_09_C09.json` |  |
| china_pw | 10 | C10 | 3033 | True | 3016 | 3033 | 32 | 15 | 522 | 3131 | 0 | 43 | 15 | 40 | 3 | 10132 | False | 25 | `results_ga\china_pw_ga_exec_10_C10.json` |  |
| croatia_tv_input | 1 | C01 | 2220 | True | 2220 | 2220 | 21 | 1 | 260 | 2165 | 0 | 26 | 8 | 24 | 2 | 1051 | False | 25 | `results_ga\croatia_tv_input_ga_exec_01_C01.json` |  |
| croatia_tv_input | 2 | C02 | 2220 | True | 2220 | 2220 | 21 | 1 | 260 | 2165 | 0 | 26 | 10 | 24 | 2 | 2060 | False | 25 | `results_ga\croatia_tv_input_ga_exec_02_C02.json` |  |
| croatia_tv_input | 3 | C03 | 2220 | True | 2220 | 2220 | 21 | 1 | 260 | 2165 | 0 | 26 | 12 | 24 | 2 | 3069 | False | 25 | `results_ga\croatia_tv_input_ga_exec_03_C03.json` |  |
| croatia_tv_input | 4 | C04 | 2220 | True | 2220 | 2220 | 21 | 1 | 260 | 2165 | 0 | 26 | 8 | 32 | 2 | 4078 | False | 25 | `results_ga\croatia_tv_input_ga_exec_04_C04.json` |  |
| croatia_tv_input | 5 | C05 | 2220 | True | 2220 | 2220 | 21 | 1 | 260 | 2165 | 0 | 26 | 10 | 32 | 2 | 5087 | False | 25 | `results_ga\croatia_tv_input_ga_exec_05_C05.json` |  |
| croatia_tv_input | 6 | C06 | 2220 | True | 2220 | 2220 | 21 | 1 | 260 | 2165 | 0 | 26 | 12 | 32 | 2 | 6096 | False | 25 | `results_ga\croatia_tv_input_ga_exec_06_C06.json` |  |
| croatia_tv_input | 7 | C07 | 2220 | True | 2220 | 2220 | 21 | 1 | 260 | 2165 | 0 | 26 | 8 | 40 | 3 | 7105 | False | 25 | `results_ga\croatia_tv_input_ga_exec_07_C07.json` |  |
| croatia_tv_input | 8 | C08 | 2220 | True | 2220 | 2220 | 21 | 1 | 260 | 2165 | 0 | 26 | 10 | 40 | 3 | 8114 | False | 25 | `results_ga\croatia_tv_input_ga_exec_08_C08.json` |  |
| croatia_tv_input | 9 | C09 | 2220 | True | 2220 | 2220 | 21 | 1 | 260 | 2165 | 0 | 26 | 12 | 40 | 3 | 9123 | False | 25 | `results_ga\croatia_tv_input_ga_exec_09_C09.json` |  |
| croatia_tv_input | 10 | C10 | 2220 | True | 2220 | 2220 | 21 | 1 | 260 | 2165 | 0 | 26 | 15 | 40 | 3 | 10132 | False | 25 | `results_ga\croatia_tv_input_ga_exec_10_C10.json` |  |
| france_iptv | 1 | C01 | 10983 | True | 10983 | 10983 | 161 | 3 | 118 | 12535 | 0 | 196 | 8 | 24 | 2 | 1051 | False | 25 | `results_ga\france_iptv_ga_exec_01_C01.json` |  |
| france_iptv | 2 | C02 | 10983 | True | 10983 | 10983 | 161 | 3 | 118 | 12535 | 0 | 196 | 10 | 24 | 2 | 2060 | False | 25 | `results_ga\france_iptv_ga_exec_02_C02.json` |  |
| france_iptv | 3 | C03 | 10983 | True | 10983 | 10983 | 161 | 3 | 118 | 12535 | 0 | 196 | 12 | 24 | 2 | 3069 | False | 25 | `results_ga\france_iptv_ga_exec_03_C03.json` |  |
| france_iptv | 4 | C04 | 10983 | True | 10983 | 10983 | 161 | 3 | 118 | 12535 | 0 | 196 | 8 | 32 | 2 | 4078 | False | 25 | `results_ga\france_iptv_ga_exec_04_C04.json` |  |
| france_iptv | 5 | C05 | 10983 | True | 10983 | 10983 | 161 | 3 | 118 | 12535 | 0 | 196 | 10 | 32 | 2 | 5087 | False | 25 | `results_ga\france_iptv_ga_exec_05_C05.json` |  |
| france_iptv | 6 | C06 | 10983 | True | 10983 | 10983 | 161 | 3 | 118 | 12535 | 0 | 196 | 12 | 32 | 2 | 6096 | False | 25 | `results_ga\france_iptv_ga_exec_06_C06.json` |  |
| france_iptv | 7 | C07 | 10983 | True | 10983 | 10983 | 161 | 3 | 118 | 12535 | 0 | 196 | 8 | 40 | 3 | 7105 | False | 25 | `results_ga\france_iptv_ga_exec_07_C07.json` |  |
| france_iptv | 8 | C08 | 10983 | True | 10983 | 10983 | 161 | 3 | 118 | 12535 | 0 | 196 | 10 | 40 | 3 | 8114 | False | 25 | `results_ga\france_iptv_ga_exec_08_C08.json` |  |
| france_iptv | 9 | C09 | 10983 | True | 10983 | 10983 | 161 | 3 | 118 | 12535 | 0 | 196 | 12 | 40 | 3 | 9123 | False | 25 | `results_ga\france_iptv_ga_exec_09_C09.json` |  |
| france_iptv | 10 | C10 | 10983 | True | 10983 | 10983 | 161 | 3 | 118 | 12535 | 0 | 196 | 15 | 40 | 3 | 10132 | False | 25 | `results_ga\france_iptv_ga_exec_10_C10.json` |  |
| germany_tv_input | 1 | C01 | 1598 | True | 1481 | 1598 | 19 | 26 | 255 | 2053 | 0 | 27 | 8 | 24 | 2 | 1051 | False | 25 | `results_ga\germany_tv_input_ga_exec_01_C01.json` |  |
| germany_tv_input | 2 | C02 | 1603 | True | 1481 | 1603 | 18 | 26 | 255 | 2048 | 0 | 27 | 10 | 24 | 2 | 2060 | False | 25 | `results_ga\germany_tv_input_ga_exec_02_C02.json` |  |
| germany_tv_input | 3 | C03 | 1598 | True | 1481 | 1598 | 19 | 26 | 255 | 2053 | 0 | 27 | 12 | 24 | 2 | 3069 | False | 25 | `results_ga\germany_tv_input_ga_exec_03_C03.json` |  |
| germany_tv_input | 4 | C04 | 1608 | True | 1481 | 1608 | 18 | 26 | 255 | 2053 | 0 | 27 | 8 | 32 | 2 | 4078 | False | 25 | `results_ga\germany_tv_input_ga_exec_04_C04.json` |  |
| germany_tv_input | 5 | C05 | 1603 | True | 1481 | 1603 | 18 | 26 | 255 | 2048 | 0 | 27 | 10 | 32 | 2 | 5087 | False | 25 | `results_ga\germany_tv_input_ga_exec_05_C05.json` |  |
| germany_tv_input | 6 | C06 | 1608 | True | 1481 | 1608 | 18 | 26 | 255 | 2053 | 0 | 27 | 12 | 32 | 2 | 6096 | False | 25 | `results_ga\germany_tv_input_ga_exec_06_C06.json` |  |
| germany_tv_input | 7 | C07 | 1608 | True | 1481 | 1608 | 18 | 26 | 255 | 2053 | 0 | 27 | 8 | 40 | 3 | 7105 | False | 25 | `results_ga\germany_tv_input_ga_exec_07_C07.json` |  |
| germany_tv_input | 8 | C08 | 1603 | True | 1481 | 1603 | 18 | 26 | 255 | 2048 | 0 | 27 | 10 | 40 | 3 | 8114 | False | 25 | `results_ga\germany_tv_input_ga_exec_08_C08.json` |  |
| germany_tv_input | 9 | C09 | 1603 | True | 1481 | 1603 | 18 | 26 | 255 | 2048 | 0 | 27 | 12 | 40 | 3 | 9123 | False | 25 | `results_ga\germany_tv_input_ga_exec_09_C09.json` |  |
| germany_tv_input | 10 | C10 | 1608 | True | 1481 | 1608 | 18 | 26 | 255 | 2053 | 0 | 27 | 15 | 40 | 3 | 10132 | False | 25 | `results_ga\germany_tv_input_ga_exec_10_C10.json` |  |
| kosovo_tv_input | 1 | C01 | 2587 | True | 2572 | 2587 | 27 | 23 | 330 | 2683 | 0 | 32 | 8 | 24 | 2 | 1051 | False | 25 | `results_ga\kosovo_tv_input_ga_exec_01_C01.json` |  |
| kosovo_tv_input | 2 | C02 | 2582 | True | 2572 | 2582 | 27 | 23 | 310 | 2698 | 0 | 32 | 10 | 24 | 2 | 2060 | False | 25 | `results_ga\kosovo_tv_input_ga_exec_02_C02.json` |  |
| kosovo_tv_input | 3 | C03 | 2591 | True | 2572 | 2591 | 27 | 23 | 360 | 2657 | 0 | 32 | 12 | 24 | 2 | 3069 | False | 25 | `results_ga\kosovo_tv_input_ga_exec_03_C03.json` |  |
| kosovo_tv_input | 4 | C04 | 2591 | True | 2572 | 2591 | 27 | 23 | 360 | 2657 | 0 | 32 | 8 | 32 | 2 | 4078 | False | 25 | `results_ga\kosovo_tv_input_ga_exec_04_C04.json` |  |
| kosovo_tv_input | 5 | C05 | 2591 | True | 2572 | 2591 | 27 | 23 | 360 | 2657 | 0 | 32 | 10 | 32 | 2 | 5087 | False | 25 | `results_ga\kosovo_tv_input_ga_exec_05_C05.json` |  |
| kosovo_tv_input | 6 | C06 | 2582 | True | 2572 | 2582 | 27 | 23 | 310 | 2698 | 0 | 32 | 12 | 32 | 2 | 6096 | False | 25 | `results_ga\kosovo_tv_input_ga_exec_06_C06.json` |  |
| kosovo_tv_input | 7 | C07 | 2591 | True | 2572 | 2591 | 27 | 23 | 360 | 2657 | 0 | 32 | 8 | 40 | 3 | 7105 | False | 25 | `results_ga\kosovo_tv_input_ga_exec_07_C07.json` |  |
| kosovo_tv_input | 8 | C08 | 2591 | True | 2572 | 2591 | 27 | 23 | 360 | 2657 | 0 | 32 | 10 | 40 | 3 | 8114 | False | 25 | `results_ga\kosovo_tv_input_ga_exec_08_C08.json` |  |
| kosovo_tv_input | 9 | C09 | 2591 | True | 2572 | 2591 | 27 | 23 | 360 | 2657 | 0 | 32 | 12 | 40 | 3 | 9123 | False | 25 | `results_ga\kosovo_tv_input_ga_exec_09_C09.json` |  |
| kosovo_tv_input | 10 | C10 | 2587 | True | 2572 | 2587 | 27 | 23 | 330 | 2683 | 0 | 32 | 15 | 40 | 3 | 10132 | False | 25 | `results_ga\kosovo_tv_input_ga_exec_10_C10.json` |  |
| netherlands_tv_input | 1 | C01 | 2634 | True | 2584 | 2634 | 27 | 21 | 205 | 2981 | 0 | 35 | 8 | 24 | 2 | 1051 | False | 25 | `results_ga\netherlands_tv_input_ga_exec_01_C01.json` |  |
| netherlands_tv_input | 2 | C02 | 2635 | True | 2584 | 2635 | 26 | 22 | 205 | 2990 | 0 | 35 | 10 | 24 | 2 | 2060 | False | 25 | `results_ga\netherlands_tv_input_ga_exec_02_C02.json` |  |
| netherlands_tv_input | 3 | C03 | 2635 | True | 2584 | 2635 | 26 | 22 | 205 | 2990 | 0 | 35 | 12 | 24 | 2 | 3069 | False | 25 | `results_ga\netherlands_tv_input_ga_exec_03_C03.json` |  |
| netherlands_tv_input | 4 | C04 | 2635 | True | 2584 | 2635 | 26 | 22 | 205 | 2990 | 0 | 35 | 8 | 32 | 2 | 4078 | False | 25 | `results_ga\netherlands_tv_input_ga_exec_04_C04.json` |  |
| netherlands_tv_input | 5 | C05 | 2634 | True | 2584 | 2634 | 27 | 21 | 205 | 2981 | 0 | 35 | 10 | 32 | 2 | 5087 | False | 25 | `results_ga\netherlands_tv_input_ga_exec_05_C05.json` |  |
| netherlands_tv_input | 6 | C06 | 2635 | True | 2584 | 2635 | 26 | 22 | 205 | 2990 | 0 | 35 | 12 | 32 | 2 | 6096 | False | 25 | `results_ga\netherlands_tv_input_ga_exec_06_C06.json` |  |
| netherlands_tv_input | 7 | C07 | 2635 | True | 2584 | 2635 | 26 | 22 | 205 | 2990 | 0 | 35 | 8 | 40 | 3 | 7105 | False | 25 | `results_ga\netherlands_tv_input_ga_exec_07_C07.json` |  |
| netherlands_tv_input | 8 | C08 | 2634 | True | 2584 | 2634 | 27 | 21 | 205 | 2981 | 0 | 35 | 10 | 40 | 3 | 8114 | False | 25 | `results_ga\netherlands_tv_input_ga_exec_08_C08.json` |  |
| netherlands_tv_input | 9 | C09 | 2634 | True | 2584 | 2634 | 27 | 21 | 205 | 2981 | 0 | 35 | 12 | 40 | 3 | 9123 | False | 25 | `results_ga\netherlands_tv_input_ga_exec_09_C09.json` |  |
| netherlands_tv_input | 10 | C10 | 2635 | True | 2584 | 2635 | 26 | 22 | 205 | 2990 | 0 | 35 | 15 | 40 | 3 | 10132 | False | 25 | `results_ga\netherlands_tv_input_ga_exec_10_C10.json` |  |
| singapore_pw | 1 | C01 | 6986 | True | 6986 | 6986 | 69 | 1 | 199 | 7497 | 0 | 101 | 8 | 24 | 2 | 1051 | False | 25 | `results_ga\singapore_pw_ga_exec_01_C01.json` |  |
| singapore_pw | 2 | C02 | 6986 | True | 6986 | 6986 | 69 | 1 | 199 | 7497 | 0 | 101 | 10 | 24 | 2 | 2060 | False | 25 | `results_ga\singapore_pw_ga_exec_02_C02.json` |  |
| singapore_pw | 3 | C03 | 6986 | True | 6986 | 6986 | 69 | 1 | 199 | 7497 | 0 | 101 | 12 | 24 | 2 | 3069 | False | 25 | `results_ga\singapore_pw_ga_exec_03_C03.json` |  |
| singapore_pw | 4 | C04 | 6986 | True | 6986 | 6986 | 69 | 1 | 199 | 7497 | 0 | 101 | 8 | 32 | 2 | 4078 | False | 25 | `results_ga\singapore_pw_ga_exec_04_C04.json` |  |
| singapore_pw | 5 | C05 | 6986 | True | 6986 | 6986 | 69 | 1 | 199 | 7497 | 0 | 101 | 10 | 32 | 2 | 5087 | False | 25 | `results_ga\singapore_pw_ga_exec_05_C05.json` |  |
| singapore_pw | 6 | C06 | 6986 | True | 6986 | 6986 | 69 | 1 | 199 | 7497 | 0 | 101 | 12 | 32 | 2 | 6096 | False | 25 | `results_ga\singapore_pw_ga_exec_06_C06.json` |  |
| singapore_pw | 7 | C07 | 6986 | True | 6986 | 6986 | 69 | 1 | 199 | 7497 | 0 | 101 | 8 | 40 | 3 | 7105 | False | 25 | `results_ga\singapore_pw_ga_exec_07_C07.json` |  |
| singapore_pw | 8 | C08 | 6986 | True | 6986 | 6986 | 69 | 1 | 199 | 7497 | 0 | 101 | 10 | 40 | 3 | 8114 | False | 25 | `results_ga\singapore_pw_ga_exec_08_C08.json` |  |
| singapore_pw | 9 | C09 | 6986 | True | 6986 | 6986 | 69 | 1 | 199 | 7497 | 0 | 101 | 12 | 40 | 3 | 9123 | False | 25 | `results_ga\singapore_pw_ga_exec_09_C09.json` |  |
| singapore_pw | 10 | C10 | 6986 | True | 6986 | 6986 | 69 | 1 | 199 | 7497 | 0 | 101 | 15 | 40 | 3 | 10132 | False | 25 | `results_ga\singapore_pw_ga_exec_10_C10.json` |  |
| spain_iptv | 1 | C01 | 6655 | True | 6655 | 6655 | 69 | 7 | 273 | 7212 | 0 | 98 | 8 | 24 | 2 | 1051 | False | 25 | `results_ga\spain_iptv_ga_exec_01_C01.json` |  |
| spain_iptv | 2 | C02 | 6655 | True | 6655 | 6655 | 69 | 7 | 273 | 7212 | 0 | 98 | 10 | 24 | 2 | 2060 | False | 25 | `results_ga\spain_iptv_ga_exec_02_C02.json` |  |
| spain_iptv | 3 | C03 | 6655 | True | 6655 | 6655 | 69 | 7 | 273 | 7212 | 0 | 98 | 12 | 24 | 2 | 3069 | False | 25 | `results_ga\spain_iptv_ga_exec_03_C03.json` |  |
| spain_iptv | 4 | C04 | 6655 | True | 6655 | 6655 | 69 | 7 | 273 | 7212 | 0 | 98 | 8 | 32 | 2 | 4078 | False | 25 | `results_ga\spain_iptv_ga_exec_04_C04.json` |  |
| spain_iptv | 5 | C05 | 6655 | True | 6655 | 6655 | 69 | 7 | 273 | 7212 | 0 | 98 | 10 | 32 | 2 | 5087 | False | 25 | `results_ga\spain_iptv_ga_exec_05_C05.json` |  |
| spain_iptv | 6 | C06 | 6655 | True | 6655 | 6655 | 69 | 7 | 273 | 7212 | 0 | 98 | 12 | 32 | 2 | 6096 | False | 25 | `results_ga\spain_iptv_ga_exec_06_C06.json` |  |
| spain_iptv | 7 | C07 | 6655 | True | 6655 | 6655 | 69 | 7 | 273 | 7212 | 0 | 98 | 8 | 40 | 3 | 7105 | False | 25 | `results_ga\spain_iptv_ga_exec_07_C07.json` |  |
| spain_iptv | 8 | C08 | 6655 | True | 6655 | 6655 | 69 | 7 | 273 | 7212 | 0 | 98 | 10 | 40 | 3 | 8114 | False | 25 | `results_ga\spain_iptv_ga_exec_08_C08.json` |  |
| spain_iptv | 9 | C09 | 6655 | True | 6655 | 6655 | 69 | 7 | 273 | 7212 | 0 | 98 | 12 | 40 | 3 | 9123 | False | 25 | `results_ga\spain_iptv_ga_exec_09_C09.json` |  |
| spain_iptv | 10 | C10 | 6655 | True | 6655 | 6655 | 69 | 7 | 273 | 7212 | 0 | 98 | 15 | 40 | 3 | 10132 | False | 25 | `results_ga\spain_iptv_ga_exec_10_C10.json` |  |
| toy | 1 | C01 | 510 | True | 510 | 510 | 2 | 1 | 130 | 400 | 0 | 5 | 8 | 24 | 2 | 1051 | False | 25 | `results_ga\toy_ga_exec_01_C01.json` |  |
| toy | 2 | C02 | 510 | True | 510 | 510 | 2 | 1 | 130 | 400 | 0 | 5 | 10 | 24 | 2 | 2060 | False | 25 | `results_ga\toy_ga_exec_02_C02.json` |  |
| toy | 3 | C03 | 510 | True | 510 | 510 | 2 | 1 | 130 | 400 | 0 | 5 | 12 | 24 | 2 | 3069 | False | 25 | `results_ga\toy_ga_exec_03_C03.json` |  |
| toy | 4 | C04 | 510 | True | 510 | 510 | 2 | 1 | 130 | 400 | 0 | 5 | 8 | 32 | 2 | 4078 | False | 25 | `results_ga\toy_ga_exec_04_C04.json` |  |
| toy | 5 | C05 | 510 | True | 510 | 510 | 2 | 1 | 130 | 400 | 0 | 5 | 10 | 32 | 2 | 5087 | False | 25 | `results_ga\toy_ga_exec_05_C05.json` |  |
| toy | 6 | C06 | 510 | True | 510 | 510 | 2 | 1 | 130 | 400 | 0 | 5 | 12 | 32 | 2 | 6096 | False | 25 | `results_ga\toy_ga_exec_06_C06.json` |  |
| toy | 7 | C07 | 510 | True | 510 | 510 | 2 | 1 | 130 | 400 | 0 | 5 | 8 | 40 | 3 | 7105 | False | 25 | `results_ga\toy_ga_exec_07_C07.json` |  |
| toy | 8 | C08 | 510 | True | 510 | 510 | 2 | 1 | 130 | 400 | 0 | 5 | 10 | 40 | 3 | 8114 | False | 25 | `results_ga\toy_ga_exec_08_C08.json` |  |
| toy | 9 | C09 | 510 | True | 510 | 510 | 2 | 1 | 130 | 400 | 0 | 5 | 12 | 40 | 3 | 9123 | False | 25 | `results_ga\toy_ga_exec_09_C09.json` |  |
| toy | 10 | C10 | 510 | True | 510 | 510 | 2 | 1 | 130 | 400 | 0 | 5 | 15 | 40 | 3 | 10132 | False | 25 | `results_ga\toy_ga_exec_10_C10.json` |  |
| uk_iptv | 1 | C01 | 9948 | True | 9948 | 9948 | 101 | 0 | 0 | 10958 | 0 | 149 | 8 | 24 | 2 | 1051 | False | 25 | `results_ga\uk_iptv_ga_exec_01_C01.json` |  |
| uk_iptv | 2 | C02 | 9948 | True | 9948 | 9948 | 101 | 0 | 0 | 10958 | 0 | 149 | 10 | 24 | 2 | 2060 | False | 25 | `results_ga\uk_iptv_ga_exec_02_C02.json` |  |
| uk_iptv | 3 | C03 | 9948 | True | 9948 | 9948 | 101 | 0 | 0 | 10958 | 0 | 149 | 12 | 24 | 2 | 3069 | False | 25 | `results_ga\uk_iptv_ga_exec_03_C03.json` |  |
| uk_iptv | 4 | C04 | 9948 | True | 9948 | 9948 | 101 | 0 | 0 | 10958 | 0 | 149 | 8 | 32 | 2 | 4078 | False | 25 | `results_ga\uk_iptv_ga_exec_04_C04.json` |  |
| uk_iptv | 5 | C05 | 9948 | True | 9948 | 9948 | 101 | 0 | 0 | 10958 | 0 | 149 | 10 | 32 | 2 | 5087 | False | 25 | `results_ga\uk_iptv_ga_exec_05_C05.json` |  |
| uk_iptv | 6 | C06 | 9948 | True | 9948 | 9948 | 101 | 0 | 0 | 10958 | 0 | 149 | 12 | 32 | 2 | 6096 | False | 25 | `results_ga\uk_iptv_ga_exec_06_C06.json` |  |
| uk_iptv | 7 | C07 | 9948 | True | 9948 | 9948 | 101 | 0 | 0 | 10958 | 0 | 149 | 8 | 40 | 3 | 7105 | False | 25 | `results_ga\uk_iptv_ga_exec_07_C07.json` |  |
| uk_iptv | 8 | C08 | 9948 | True | 9948 | 9948 | 101 | 0 | 0 | 10958 | 0 | 149 | 10 | 40 | 3 | 8114 | False | 25 | `results_ga\uk_iptv_ga_exec_08_C08.json` |  |
| uk_iptv | 9 | C09 | 9948 | True | 9948 | 9948 | 101 | 0 | 0 | 10958 | 0 | 149 | 12 | 40 | 3 | 9123 | False | 25 | `results_ga\uk_iptv_ga_exec_09_C09.json` |  |
| uk_iptv | 10 | C10 | 9948 | True | 9948 | 9948 | 101 | 0 | 0 | 10958 | 0 | 149 | 15 | 40 | 3 | 10132 | False | 25 | `results_ga\uk_iptv_ga_exec_10_C10.json` |  |
| uk_tv_input | 1 | C01 | 2266 | True | 2266 | 2266 | 21 | 0 | 250 | 2226 | 0 | 26 | 8 | 24 | 2 | 1051 | False | 25 | `results_ga\uk_tv_input_ga_exec_01_C01.json` |  |
| uk_tv_input | 2 | C02 | 2266 | True | 2266 | 2266 | 21 | 0 | 250 | 2226 | 0 | 26 | 10 | 24 | 2 | 2060 | False | 25 | `results_ga\uk_tv_input_ga_exec_02_C02.json` |  |
| uk_tv_input | 3 | C03 | 2266 | True | 2266 | 2266 | 21 | 0 | 250 | 2226 | 0 | 26 | 12 | 24 | 2 | 3069 | False | 25 | `results_ga\uk_tv_input_ga_exec_03_C03.json` |  |
| uk_tv_input | 4 | C04 | 2266 | True | 2266 | 2266 | 21 | 0 | 250 | 2226 | 0 | 26 | 8 | 32 | 2 | 4078 | False | 25 | `results_ga\uk_tv_input_ga_exec_04_C04.json` |  |
| uk_tv_input | 5 | C05 | 2266 | True | 2266 | 2266 | 21 | 0 | 250 | 2226 | 0 | 26 | 10 | 32 | 2 | 5087 | False | 25 | `results_ga\uk_tv_input_ga_exec_05_C05.json` |  |
| uk_tv_input | 6 | C06 | 2266 | True | 2266 | 2266 | 21 | 0 | 250 | 2226 | 0 | 26 | 12 | 32 | 2 | 6096 | False | 25 | `results_ga\uk_tv_input_ga_exec_06_C06.json` |  |
| uk_tv_input | 7 | C07 | 2266 | True | 2266 | 2266 | 21 | 0 | 250 | 2226 | 0 | 26 | 8 | 40 | 3 | 7105 | False | 25 | `results_ga\uk_tv_input_ga_exec_07_C07.json` |  |
| uk_tv_input | 8 | C08 | 2266 | True | 2266 | 2266 | 21 | 0 | 250 | 2226 | 0 | 26 | 10 | 40 | 3 | 8114 | False | 25 | `results_ga\uk_tv_input_ga_exec_08_C08.json` |  |
| uk_tv_input | 9 | C09 | 2266 | True | 2266 | 2266 | 21 | 0 | 250 | 2226 | 0 | 26 | 12 | 40 | 3 | 9123 | False | 25 | `results_ga\uk_tv_input_ga_exec_09_C09.json` |  |
| uk_tv_input | 10 | C10 | 2266 | True | 2266 | 2266 | 21 | 0 | 250 | 2226 | 0 | 26 | 15 | 40 | 3 | 10132 | False | 25 | `results_ga\uk_tv_input_ga_exec_10_C10.json` |  |
| us_iptv | 1 | C01 | 5560 | True | 5560 | 5560 | 54 | 2 | 106 | 6034 | 0 | 78 | 8 | 24 | 2 | 1051 | False | 25 | `results_ga\us_iptv_ga_exec_01_C01.json` |  |
| us_iptv | 2 | C02 | 5560 | True | 5560 | 5560 | 54 | 2 | 106 | 6034 | 0 | 78 | 10 | 24 | 2 | 2060 | False | 25 | `results_ga\us_iptv_ga_exec_02_C02.json` |  |
| us_iptv | 3 | C03 | 5560 | True | 5560 | 5560 | 54 | 2 | 106 | 6034 | 0 | 78 | 12 | 24 | 2 | 3069 | False | 25 | `results_ga\us_iptv_ga_exec_03_C03.json` |  |
| us_iptv | 4 | C04 | 5560 | True | 5560 | 5560 | 54 | 2 | 106 | 6034 | 0 | 78 | 8 | 32 | 2 | 4078 | False | 25 | `results_ga\us_iptv_ga_exec_04_C04.json` |  |
| us_iptv | 5 | C05 | 5560 | True | 5560 | 5560 | 54 | 2 | 106 | 6034 | 0 | 78 | 10 | 32 | 2 | 5087 | False | 25 | `results_ga\us_iptv_ga_exec_05_C05.json` |  |
| us_iptv | 6 | C06 | 5560 | True | 5560 | 5560 | 54 | 2 | 106 | 6034 | 0 | 78 | 12 | 32 | 2 | 6096 | False | 25 | `results_ga\us_iptv_ga_exec_06_C06.json` |  |
| us_iptv | 7 | C07 | 5560 | True | 5560 | 5560 | 54 | 2 | 106 | 6034 | 0 | 78 | 8 | 40 | 3 | 7105 | False | 25 | `results_ga\us_iptv_ga_exec_07_C07.json` |  |
| us_iptv | 8 | C08 | 5560 | True | 5560 | 5560 | 54 | 2 | 106 | 6034 | 0 | 78 | 10 | 40 | 3 | 8114 | False | 25 | `results_ga\us_iptv_ga_exec_08_C08.json` |  |
| us_iptv | 9 | C09 | 5560 | True | 5560 | 5560 | 54 | 2 | 106 | 6034 | 0 | 78 | 12 | 40 | 3 | 9123 | False | 25 | `results_ga\us_iptv_ga_exec_09_C09.json` |  |
| us_iptv | 10 | C10 | 5560 | True | 5560 | 5560 | 54 | 2 | 106 | 6034 | 0 | 78 | 15 | 40 | 3 | 10132 | False | 25 | `results_ga\us_iptv_ga_exec_10_C10.json` |  |
| usa_tv_input | 1 | C01 | 3597 | True | 3579 | 3597 | 31 | 1 | 565 | 3237 | 0 | 34 | 8 | 24 | 2 | 1051 | False | 25 | `results_ga\usa_tv_input_ga_exec_01_C01.json` |  |
| usa_tv_input | 2 | C02 | 3601 | True | 3579 | 3601 | 32 | 2 | 565 | 3296 | 0 | 35 | 10 | 24 | 2 | 2060 | False | 25 | `results_ga\usa_tv_input_ga_exec_02_C02.json` |  |
| usa_tv_input | 3 | C03 | 3598 | True | 3579 | 3598 | 32 | 2 | 565 | 3293 | 0 | 35 | 12 | 24 | 2 | 3069 | False | 25 | `results_ga\usa_tv_input_ga_exec_03_C03.json` |  |
| usa_tv_input | 4 | C04 | 3598 | True | 3579 | 3598 | 32 | 2 | 565 | 3293 | 0 | 35 | 8 | 32 | 2 | 4078 | False | 25 | `results_ga\usa_tv_input_ga_exec_04_C04.json` |  |
| usa_tv_input | 5 | C05 | 3598 | True | 3579 | 3598 | 32 | 2 | 565 | 3293 | 0 | 35 | 10 | 32 | 2 | 5087 | False | 25 | `results_ga\usa_tv_input_ga_exec_05_C05.json` |  |
| usa_tv_input | 6 | C06 | 3597 | True | 3579 | 3597 | 31 | 1 | 565 | 3237 | 0 | 34 | 12 | 32 | 2 | 6096 | False | 25 | `results_ga\usa_tv_input_ga_exec_06_C06.json` |  |
| usa_tv_input | 7 | C07 | 3598 | True | 3579 | 3598 | 32 | 2 | 565 | 3293 | 0 | 35 | 8 | 40 | 3 | 7105 | False | 25 | `results_ga\usa_tv_input_ga_exec_07_C07.json` |  |
| usa_tv_input | 8 | C08 | 3598 | True | 3579 | 3598 | 32 | 2 | 565 | 3293 | 0 | 35 | 10 | 40 | 3 | 8114 | False | 25 | `results_ga\usa_tv_input_ga_exec_08_C08.json` |  |
| usa_tv_input | 9 | C09 | 3598 | True | 3579 | 3598 | 32 | 2 | 565 | 3293 | 0 | 35 | 12 | 40 | 3 | 9123 | False | 25 | `results_ga\usa_tv_input_ga_exec_09_C09.json` |  |
| usa_tv_input | 10 | C10 | 3598 | True | 3579 | 3598 | 32 | 2 | 565 | 3293 | 0 | 35 | 15 | 40 | 3 | 10132 | False | 25 | `results_ga\usa_tv_input_ga_exec_10_C10.json` |  |
| youtube_gold | 1 | C01 | 107439 | True | 107435 | 107439 | 3424 | 3456 | 42356 | 288891 | 0 | 3457 | 8 | 24 | 2 | 1051 | False | 25 | `results_ga\youtube_gold_ga_exec_01_C01.json` |  |
| youtube_gold | 2 | C02 | 107439 | True | 107435 | 107439 | 3424 | 3456 | 42356 | 288891 | 0 | 3457 | 10 | 24 | 2 | 2060 | False | 25 | `results_ga\youtube_gold_ga_exec_02_C02.json` |  |
| youtube_gold | 3 | C03 | 107439 | True | 107435 | 107439 | 3424 | 3456 | 42356 | 288891 | 0 | 3457 | 12 | 24 | 2 | 3069 | False | 25 | `results_ga\youtube_gold_ga_exec_03_C03.json` |  |
| youtube_gold | 4 | C04 | 107435 | True | 107435 | 107435 | 3424 | 3456 | 42356 | 288891 | 0 | 3457 | 8 | 32 | 2 | 4078 | False | 25 | `results_ga\youtube_gold_ga_exec_04_C04.json` |  |
| youtube_gold | 5 | C05 | 107435 | True | 107435 | 107435 | 3424 | 3456 | 42356 | 288891 | 0 | 3457 | 10 | 32 | 2 | 5087 | False | 25 | `results_ga\youtube_gold_ga_exec_05_C05.json` |  |
| youtube_gold | 6 | C06 | 107435 | True | 107435 | 107435 | 3424 | 3456 | 42356 | 288891 | 0 | 3457 | 12 | 32 | 2 | 6096 | False | 25 | `results_ga\youtube_gold_ga_exec_06_C06.json` |  |
| youtube_gold | 7 | C07 | 107435 | True | 107435 | 107435 | 3424 | 3456 | 42356 | 288891 | 0 | 3457 | 8 | 40 | 3 | 7105 | False | 25 | `results_ga\youtube_gold_ga_exec_07_C07.json` |  |
| youtube_gold | 8 | C08 | 107435 | True | 107435 | 107435 | 3424 | 3456 | 42356 | 288891 | 0 | 3457 | 10 | 40 | 3 | 8114 | False | 25 | `results_ga\youtube_gold_ga_exec_08_C08.json` |  |
| youtube_gold | 9 | C09 | 107435 | True | 107435 | 107435 | 3424 | 3456 | 42356 | 288891 | 0 | 3457 | 12 | 40 | 3 | 9123 | False | 25 | `results_ga\youtube_gold_ga_exec_09_C09.json` |  |
| youtube_gold | 10 | C10 | 107435 | True | 107435 | 107435 | 3424 | 3456 | 42356 | 288891 | 0 | 3457 | 15 | 40 | 3 | 10132 | False | 25 | `results_ga\youtube_gold_ga_exec_10_C10.json` |  |
| youtube_premium | 1 | C01 | 67862 | True | 67862 | 67862 | 780 | 83 | 23408 | 63906 | 0 | 786 | 8 | 24 | 2 | 1051 | False | 25 | `results_ga\youtube_premium_ga_exec_01_C01.json` |  |
| youtube_premium | 2 | C02 | 67862 | True | 67862 | 67862 | 780 | 83 | 23408 | 63906 | 0 | 786 | 10 | 24 | 2 | 2060 | False | 25 | `results_ga\youtube_premium_ga_exec_02_C02.json` |  |
| youtube_premium | 3 | C03 | 67862 | True | 67862 | 67862 | 780 | 83 | 23408 | 63906 | 0 | 786 | 12 | 24 | 2 | 3069 | False | 25 | `results_ga\youtube_premium_ga_exec_03_C03.json` |  |
| youtube_premium | 4 | C04 | 67862 | True | 67862 | 67862 | 780 | 83 | 23408 | 63906 | 0 | 786 | 8 | 32 | 2 | 4078 | False | 25 | `results_ga\youtube_premium_ga_exec_04_C04.json` |  |
| youtube_premium | 5 | C05 | 67862 | True | 67862 | 67862 | 780 | 83 | 23408 | 63906 | 0 | 786 | 10 | 32 | 2 | 5087 | False | 25 | `results_ga\youtube_premium_ga_exec_05_C05.json` |  |
| youtube_premium | 6 | C06 | 67862 | True | 67862 | 67862 | 780 | 83 | 23408 | 63906 | 0 | 786 | 12 | 32 | 2 | 6096 | False | 25 | `results_ga\youtube_premium_ga_exec_06_C06.json` |  |
| youtube_premium | 7 | C07 | 67862 | True | 67862 | 67862 | 780 | 83 | 23408 | 63906 | 0 | 786 | 8 | 40 | 3 | 7105 | False | 25 | `results_ga\youtube_premium_ga_exec_07_C07.json` |  |
| youtube_premium | 8 | C08 | 67862 | True | 67862 | 67862 | 780 | 83 | 23408 | 63906 | 0 | 786 | 10 | 40 | 3 | 8114 | False | 25 | `results_ga\youtube_premium_ga_exec_08_C08.json` |  |
| youtube_premium | 9 | C09 | 67862 | True | 67862 | 67862 | 780 | 83 | 23408 | 63906 | 0 | 786 | 12 | 40 | 3 | 9123 | False | 25 | `results_ga\youtube_premium_ga_exec_09_C09.json` |  |
| youtube_premium | 10 | C10 | 67862 | True | 67862 | 67862 | 780 | 83 | 23408 | 63906 | 0 | 786 | 15 | 40 | 3 | 10132 | False | 25 | `results_ga\youtube_premium_ga_exec_10_C10.json` |  |