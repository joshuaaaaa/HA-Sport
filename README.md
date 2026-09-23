# HA Sport CZ/SK 🏒⚽🏀

Integrace pro Home Assistant na **fotbal, hokej a basketbal v Česku a na Slovensku**.
Ukazuje nadcházející zápasy, živé skóre, výsledky, tabulky, **pavouky play-off**, **kurzy**
a **kde se dá zápas sledovat** (TV / stream). Kurzy porovnává z více sázkových kanceláří a dává je
i jako senzory pro automatizace. Po kliknutí na zápas ukáže detail jako na Livesportu (střelci, karty,
statistiky, sestavy, vzájemné zápasy). Oblíbeným týmům posílá oznámení: připomenutí před začátkem,
góly se jménem střelce, červené karty, sestavy, pohyb kurzu, průběžné stavy a konečný výsledek.

![Náhled karet](docs/preview.png)

## Co umí

| Oblast | Funkce |
|---|---|
| **Soutěže** | Automaticky najde všechny soutěže CZ/SK pro zvolené sporty (Chance Liga, Chance Národní liga, MOL Cup, Niké liga, Slovnaft Cup, Tipsport extraliga, Chance liga (hokej), Tipsport liga SK, Maxa/Kooperativa NBL, Tipos SBL, ženské a mládežnické soutěže…) |
| **Mládež a nižší soutěže SZĽH** | Soutěže z [HockeySlovakia.sk](https://www.hockeyslovakia.sk/sk/stats/tournaments), které Sofascore nemá – např. Liga mladších žiakov 6. ročník, 1. liga mladších žiakov, krajské a regionální ligy: tabulky (vč. bodů na zápas), program, výsledky, oblíbené týmy se senzory, kalendář a připomenutí |
| **Zápasy** | Nadcházející, živé (minuta / třetina / čtvrtina), výsledky, datum a čas, kolo, stadion a město |
| **Tabulky** | Pořadí, body, skóre, barevné označení postupových a sestupových míst, zvýraznění oblíbených týmů |
| **Pavouk** | Play-off / pohárový pavouk: stav série, vítěz, živé série, termín dalšího zápasu a kurz |
| **Kurzy** | 1 / X / 2 z **více zdrojů** – výchozí zdroj Sofascore + české/slovenské sázkové kanceláře (dle Sofascore) + volitelně The Odds API. Porovnání sázkovek, **nejlepší kurz**, otevírací kurz a jeho změna, pravděpodobnost výhry (průměr sázkovek bez marže), **senzory kurzů pro automatizace**, upozornění na pohyb kurzu |
| **Kde sledovat** | TV kanály ze zdroje dat a odkazy na streamy (Oneplay, ČT sport, Voyo, JOJ Šport / JOJ Play, STVR, TVCOM, Tipsport TV, Tipos TV…). Když zdroj kanál neuvádí, odhadne vysílatele podle práv dané soutěže (v kartě označeno `*`). |
| **Oblíbené týmy** | Každý má vlastní zařízení se senzory: příští zápas (s kurzem na váš tým), poslední výsledek, forma (V/R/P), pozice v tabulce, „právě hraje“, „hraje dnes“ |
| **Filtr** | Hledání podle názvu týmu, soutěže, **města** nebo stadionu (bez ohledu na diakritiku), podle sportu, jen oblíbené |
| **Oznámení** | X minut před začátkem (víc časů najednou, i vlastní), začátek zápasu, góly **se jménem střelce**, **červené karty**, **zveřejněné sestavy**, **pohyb kurzu**, konec poločasu/třetiny, průběžný stav každých N minut, konečný výsledek, tichý režim, push na mobil s tlačítkem **📺 Sledovat** |
| **Kalendáře** | `calendar.*_zapasy` a `calendar.*_zapasy_oblibenych` – fungují v kalendáři HA i v automatizacích |
| **Karty** | Zápasy s filtrem, můj tým, chytrá karta, pavouk, tabulka – s vizuálním editorem (samostatný soubor `card/ha-sport-card.js`, instaluje se zvlášť) |
| **Detail zápasu** | Jako na Livesportu: průběh (góly se střelci a asistencemi, karty, VAR), statistiky (držení míče, střely, xG…), sestavy s rozestavením a chybějícími hráči, vzájemné zápasy, tip fanoušků |
| **Automatizace** | Senzory kurzu a pravděpodobnosti výhry, události `ha_sport_notification`, `ha_sport_match_update` a `ha_sport_odds_change`, služby vracející data (`get_matches`, `get_team`, `get_event`, `search_team`) |

## Instalace

### HACS (doporučeno)
1. HACS → Integrace → ⋮ → *Vlastní repozitáře* → přidejte `https://github.com/joshuaaaaa/HA-Sport`, kategorie **Integrace**.
2. Nainstalujte **HA Sport CZ/SK** a restartujte Home Assistant.

### Ručně
Zkopírujte složku `custom_components/ha_sport` do `config/custom_components/` a restartujte HA.

### Aktualizace
Repozitář zatím nemá vydané verze (releases), HACS proto novou verzi sám hned nenabídne:

1. HACS → **HA Sport CZ/SK** → **⋮ → Update information** (Aktualizovat informace).
2. **⋮ → Redownload** (Stáhnout znovu) → potvrdit.
3. **Restartujte Home Assistant** (*Nastavení → Systém → Restartovat*) – znovunačtení integrace nestačí.
4. V prohlížeči **Ctrl+F5** (texty dialogů se ukládají do mezipaměti prohlížeče).
5. Kartu aktualizujte zvlášť – viz [Karta na nástěnku](#karta-na-nástěnku-instaluje-se-zvlášť).

Nainstalovanou verzi integrace najdete v *Nastavení → Zařízení a služby → HA Sport CZ/SK* (u zařízení).

### Nastavení
*Nastavení → Zařízení a služby → Přidat integraci → HA Sport CZ/SK*

1. **Sporty a země**: fotbal / hokej / basketbal, Česko / Slovensko.
2. **Soutěže**: hlavní ligy a poháry jsou předvybrané. Při hokeji + Slovensku jsou v seznamu i soutěže SZĽH
   (mládež, nižší ligy) a pole **Odkaz na soutěž SZĽH** – je předvyplněné odkazem na *Ligu mladších žiakov AA*
   (stačí potvrdit, nebo smazat / přepsat).
3. **Oblíbené týmy**: vyberte ze seznamu týmů zvolených soutěží nebo vyhledejte jiný tým (např. reprezentaci „Česko“,
   klub z jiné soutěže). Pokud je v seznamu **HKM Zvolen**, je předvybraný.
4. **Oznámení**: kdy a kam je posílat.

Všechno jde později změnit přes **Konfigurovat**:

| Položka | Co v ní je |
|---|---|
| **Soutěže** | výběr soutěží (Sofascore + „🏒 SZĽH · …“) a pole pro vložení odkazu na soutěž SZĽH |
| **Soutěže SZĽH (mládež, nižší ligy)** | samostatné hledání jen v soutěžích HockeySlovakia.sk (lze vložit i odkaz) |
| **Oblíbené týmy** | výběr a vyhledání oblíbených týmů (i týmů soutěží SZĽH) |
| **Oznámení** | kdy, o čem a kam posílat oznámení |
| **Obecné** | intervaly obnovy, počet dní, kurzy (počet sázkovek, The Odds API), TV, adresa API |

### Mládežnické a nižší soutěže SZĽH (HockeySlovakia.sk)

Soutěže, které Sofascore nemá – dětské a mládežnické ligy (např. **Liga mladších žiakov AA**, Liga mladších žiakov
6. ročník / HP6), krajské a regionální soutěže. Data se čtou z [HockeySlovakia.sk](https://www.hockeyslovakia.sk/sk/stats/tournaments),
oficiálního webu Slovenského zväzu ľadového hokeja.

**Přidání soutěže** – *Konfigurovat → Soutěže* (nebo přímo při prvním nastavení), jeden ze způsobů:

* **Vložit odkaz** do pole *Odkaz na soutěž SZĽH*, např.
  `https://www.hockeyslovakia.sk/sk/stats/results/1207/liga-mladsich-ziakov-aa`
  (jakákoliv stránka soutěže – program a výsledky, tabulka, přehled; více odkazů oddělte čárkou).
  Název soutěže se načte z titulku stránky. Pole je **předvyplněné odkazem na Ligu mladších žiakov AA**,
  dokud ji nemáte přidanou – stačí potvrdit, nebo odkaz smazat či přepsat.
* **Vybrat ze seznamu** – při zvoleném hokeji a Slovensku jsou soutěže SZĽH v seznamu jako **„🏒 SZĽH · …“**;
  do pole *Hledat* napište např. `mladší žiaci`, `6. ročník` nebo `AA`. Pod popisem kroku je řádek se stavem
  načtení (`SZĽH (HockeySlovakia.sk): ✅ počet` nebo `❌ chyba`).
* **Samostatné hledání** – *Konfigurovat → Soutěže SZĽH (mládež, nižší ligy)*.

**Oblíbený tým** – v *Konfigurovat → Oblíbené týmy* jsou i týmy soutěží SZĽH; **HKM Zvolen** je předvybraný.

**Odebrání / změna** – v *Konfigurovat → Soutěže* soutěž odškrtněte, případně vložte jiný odkaz. Změny se projeví
hned po uložení (integrace se sama znovu načte).

Soutěž se chová jako ostatní: senzor soutěže, tabulka (včetně sloupce **B/Z** – body na zápas), program a výsledky
v kartě, oblíbený tým má senzory příštího zápasu, posledního výsledku, formy a pozice, kalendář a připomenutí
před zápasem. HockeySlovakia.sk nemá veřejné API, data se čtou z jejich webových stránek (obnova v běžném intervalu,
výsledek zápasu se objeví po jeho zapsání svazem). U těchto soutěží nejsou kurzy, streamy, živé skóre ani loga týmů.

Specifika dětských soutěží, se kterými integrace počítá:
* **Datum bez roku** („So 27.09.“) – rok se doplní podle sezóny (i přes přelom roku).
* **Zápas bez uvedeného času** – v kartě se místo času zobrazí „—“, v kalendáři je celodenní událost
  a z připomenutí se pošle jen to „den předem“ (kratší by podle neznámého času nedávala smysl).
* **Odehraný zápas bez zapsaného výsledku** – stav „Výsledek zatím nezapsán“ (bez odpočtu).
* **Tabulky střelců / hráčů** na stránce tabulky se ignorují, načte se jen tabulka týmů.

Karty pro soutěž SZĽH (stačí název nebo jeho část):
```yaml
type: custom:ha-sport-standings-card
competition: Liga mladších žiakov AA
---
type: custom:ha-sport-card
mode: matches
competition: mladších žiakov AA
show_filter: false
---
type: custom:ha-sport-team-card
team: HKM Zvolen
```

### Karta na nástěnku (instaluje se zvlášť)
Integrace a karta jsou dvě samostatné věci – HACS z jednoho repozitáře nainstaluje jen integraci.
Kartu přidáte ručně:

1. Stáhněte [`card/ha-sport-card.js`](card/ha-sport-card.js) a uložte ho do `/config/www/ha-sport-card.js`
   (složku `www` případně vytvořte; po jejím prvním vytvoření restartujte HA).
2. *Nastavení → Nástěnky → ⋮ → Zdroje → Přidat zdroj*
   * URL: `/local/ha-sport-card.js?v=1.3.1`
   * Typ: **JavaScript modul**
3. Obnovte prohlížeč (Ctrl+F5, v mobilní aplikaci *Nastavení → Aplikace → Obnovit frontend*).

Při aktualizaci karty soubor přepište a zvyšte číslo ve `?v=`, aby prohlížeč nepoužil starou verzi z mezipaměti.
Karta potřebuje nainstalovanou a nastavenou integraci (bere z ní data).

## Karty na nástěnku

Po přidání zdroje najdete karty v nabídce „Přidat kartu“ (hledejte „HA Sport“), všechny mají vizuální editor.

Soutěž a tým stačí zadat **názvem** (`competition: Chance Liga`, `team: Sparta`, stačí i část názvu, na diakritice nezáleží).
Číselná ID (`competition_id`, `team_id`) jsou volitelná – najdete je v atributech `competition_ids` a `team_ids`
senzoru **Poslední aktualizace** (*Nastavení → Zařízení a služby → HA Sport CZ/SK → zařízení → Diagnostika*).
Když karta soutěž nebo tým nenajde, vypíše seznam dostupných názvů i s ID.

### Zápasy s filtrem
```yaml
type: custom:ha-sport-card
mode: matches          # nadcházející / živě / výsledky + hledání + filtr podle sportu
title: Zápasy CZ/SK
# sport: ice-hockey     # jen jeden sport
# competition: Chance Liga   # jen jedna soutěž – stačí název (nebo competition_id: 172)
# city: Brno            # pevný filtr podle města
# favorites_only: true
# days: 14
# show_detail: false    # vypnout detail zápasu po kliknutí
```
Kliknutím na zápas se otevře detail jako na Livesportu: průběh (góly, karty), statistiky, kurzy všech sázkovek,
vzájemné zápasy, tip fanoušků a sestavy.

### Můj tým – příští zápas s kurzem
```yaml
type: custom:ha-sport-team-card
# team: Sparta   # název oblíbeného týmu (nebo team_id); bez něj zobrazí všechny oblíbené
days: 7
```
Ukazuje loga, datum a odpočet, kurzy 1/X/2 se zvýrazněním vašeho týmu a pravděpodobností, nejlepší kurz,
vzájemné zápasy, tip fanoušků, střelce během zápasu,
tlačítko streamu, zvonek pro oznámení, formu, pozici v tabulce a další zápasy v týdnu.
Během zápasu zobrazuje živé skóre a minutu.

### Chytrá karta (kurz na můj tým, nebo pavouk)
```yaml
type: custom:ha-sport-smart-card
competition: Tipsport extraliga   # soutěž, jejíž pavouk/tabulka se ukáže, když oblíbené týmy tento týden nehrají
days: 7
```
Když některý oblíbený tým hraje v příštích `days` dnech, ukáže zápas s kurzem. Jinak ukáže
pavouka vybrané soutěže (nebo tabulku, pokud soutěž pavouka nemá).

### Pavouk
```yaml
type: custom:ha-sport-bracket-card
competition: Tipsport extraliga
```

### Tabulka
```yaml
type: custom:ha-sport-standings-card
competition: Chance Liga
max_rows: 10
short_names: true
```

## Entity

| Entita | Popis |
|---|---|
| `sensor.<soutez>` | Čas příštího zápasu soutěže. Atributy: `upcoming`, `results`, `live`, `standings`, `leader`, `has_bracket`, `competition_id` |
| `sensor.<tym>_pristi_zapas` | Čas příštího / probíhajícího zápasu. Atributy: `opponent`, `home_away`, `odds_team`, `odds_draw`, `odds_opponent`, `win_probability`, `tv`, `stream_url`, `score`, `minute`, `starts_in_minutes`, `this_week`, `form`, `odds_best_team`, `odds_best_bookmaker`, `bookmakers`, `h2h`, `fans_vote`, `lineups_confirmed`, `goals` |
| `sensor.<tym>_posledni_vysledek` | např. `Sparta 2:1 Slavia`, atribut `result` (výhra/remíza/prohra), `form` |
| `sensor.<tym>_pozice_v_tabulce` | pozice, body, skóre |
| `sensor.<tym>_kurz_na_vyhru` | **kurz na výhru** vašeho týmu v příštím zápase (číslo, s historií). Atributy: `odds_draw`, `odds_opponent`, `best_odds`, `best_bookmaker`, `opening`, `change_pct`, `trend`, `is_favorite`, `bookmakers`, `match`, `start` |
| `sensor.<tym>_pravdepodobnost_vyhry` | pravděpodobnost výhry v % (z kurzů, bez marže). Atributy: `draw_probability`, `opponent_probability`, `fans_vote` |
| `binary_sensor.<tym>_prave_hraje` | zapnuto během zápasu, atributy skóre a minuta |
| `binary_sensor.<tym>_hraje_dnes` | zapnuto, když tým dnes hraje |
| `binary_sensor.*_oblibeny_tym_hraje` | hraje kterýkoliv oblíbený tým |
| `sensor.*_zive_zapasy`, `sensor.*_dnesni_zapasy`, `sensor.*_zapasy_oblibenych_tento_tyden` | počty a seznamy zápasů |
| `calendar.*_zapasy`, `calendar.*_zapasy_oblibenych` | kalendáře zápasů (s kurzy a odkazy na stream v popisu) |
| `switch.*_oznameni`, `switch.*_ziva_oznameni` | rychlé vypnutí oznámení (např. na dovolené) |
| `button.*_obnovit_data`, `button.*_testovaci_oznameni` | |

## Oznámení

Nastavení → HA Sport → Konfigurovat → **Oznámení**:

* **Pro které zápasy**: oblíbené týmy + ručně sledované / jen ručně sledované / všechny zápasy vybraných soutěží.
  Jednotlivý zápas zapnete **zvonkem 🔔** v kartě nebo službou `ha_sport.follow_match`.
* **Upozornit před začátkem**: libovolná kombinace (5 min … 1 den), lze zadat i vlastní počet minut.
* **Začátek, góly, přestávky, konec**: každé zvlášť. U basketbalu se jednotlivé koše neoznamují.
* **Góly** obsahují jméno střelce a asistenci (u oblíbených a sledovaných zápasů).
* **Červené karty** (i druhá žlutá) – lze vypnout.
* **Zveřejněné sestavy** – zhruba hodinu před zápasem přijde rozestavení a základní sestava obou týmů.
* **Pohyb kurzu na můj tým** – oznámení, když se kurz změní o nastavené % (výchozí 10 %).
* **Průběžný stav každých N minut**: 0 = vypnuto, jinak třeba každých 15 minut aktuální skóre.
* **Kam**: libovolné `notify.*` služby (mobilní aplikace dostane tlačítka *📺 Sledovat* a *Detail zápasu*, oznámení se stejným zápasem se nahrazují), nebo oznámení přímo v HA.
* **Tichý režim**: v nastaveném čase se nic neposílá.

Při živém zápasu se data obnovují automaticky rychleji (výchozí 60 s, od 20 minut před začátkem).

### Kurzy z více zdrojů

1. **Sofascore – výchozí poskytovatel** kurzů.
2. **České / slovenské sázkové kanceláře**, které Sofascore nabízí pro vaši zemi. U zápasů oblíbených týmů
   a sledovaných zápasů se porovná až *N* sázkovek (*Konfigurovat → Obecné → Počet sázkových kanceláří*).
   U ostatních zápasů se použijí jen tehdy, když výchozí poskytovatel kurz nemá, což je u české ligy časté.
3. **The Odds API** (volitelné): v *Konfigurovat → Obecné* vložte zdarma získaný API klíč (500 dotazů měsíčně).
   Kurzy se stahují jen pro sporty, které se týkají Česka nebo Slovenska, a jen jednou za nastavený počet hodin.

Výsledek: kurz 1/X/2, tabulka všech sázkovek, **nejlepší kurz** a kde je, otevírací kurz a jeho změna v %.
Stav zdrojů najdete v atributu `odds` senzoru **Poslední aktualizace** (kolik zápasů má kurz, jaké sázkovky se použily,
kolik dotazů na The Odds API zbývá).

### Vlastní automatizace
Každé oznámení vyvolá událost `ha_sport_notification` (i v tichém režimu a když jsou oznámení vypnutá),
takže si můžete postavit vlastní reakce:

```yaml
automation:
  - alias: "Gól Sparty – bliknout světlem"
    trigger:
      - platform: event
        event_type: ha_sport_notification
        event_data:
          kind: score
    condition: "{{ 'Sparta' in trigger.event.data.home or 'Sparta' in trigger.event.data.away }}"
    action:
      - service: light.turn_on
        target: {entity_id: light.obyvak}
        data: {flash: long, color_name: red}

  - alias: "Zapnout TV 5 minut před zápasem"
    trigger:
      - platform: event
        event_type: ha_sport_notification
        event_data: {kind: pre_match, minutes: 5}
    action:
      - service: media_player.turn_on
        target: {entity_id: media_player.televize}
```

`kind` může být `pre_match`, `start`, `score`, `red_card`, `lineups`, `odds_change`, `period`, `live_update`, `end`.

Další události: `ha_sport_match_update` (změna skóre nebo stavu) a `ha_sport_odds_change`. Ta se vyvolá vždy,
když se kurz na oblíbený tým pohne o nastavené procento; data jsou `outcome`, `old_odds`, `new_odds` a `change_pct`.

```yaml
automation:
  - alias: "Kurz na Spartu je pod 1.80 – připomenout tiket"
    trigger:
      - platform: numeric_state
        entity_id: sensor.ac_sparta_praha_kurz_na_vyhru
        below: 1.8
    action:
      - service: notify.mobile_app_telefon
        data:
          title: "Sparta je jasný favorit"
          message: >
            {{ state_attr('sensor.ac_sparta_praha_kurz_na_vyhru', 'match') }}:
            kurz {{ states('sensor.ac_sparta_praha_kurz_na_vyhru') }}
            (nejlepší {{ state_attr('sensor.ac_sparta_praha_kurz_na_vyhru', 'best_odds') }}
            u {{ state_attr('sensor.ac_sparta_praha_kurz_na_vyhru', 'best_bookmaker') }})

  - alias: "Kurz se výrazně pohnul"
    trigger:
      - platform: event
        event_type: ha_sport_odds_change
    action:
      - service: persistent_notification.create
        data:
          message: "{{ trigger.event.data.home }} – {{ trigger.event.data.away }}: {{ trigger.event.data.old_odds }} → {{ trigger.event.data.new_odds }} ({{ trigger.event.data.change_pct }} %)"
```

## Služby

| Služba | Popis |
|---|---|
| `ha_sport.get_matches` | vrátí zápasy podle filtru (`sport`, `competition_id`, `team_id`, `query`, `city`, `status`, `favorites_only`, `days_ahead`, `days_back`, `limit`) |
| `ha_sport.get_team` | příští a poslední zápas, forma, pozice |
| `ha_sport.get_event` | kompletní detail zápasu: střelci, karty, statistiky, sestavy, vzájemné zápasy, tip fanoušků, kurzy všech sázkovek |
| `ha_sport.search_team` | vyhledá tým (i reprezentaci) podle názvu nebo města |
| `ha_sport.add_favorite` / `remove_favorite` | správa oblíbených týmů |
| `ha_sport.follow_match` / `unfollow_match` / `mute_match` | oznámení pro konkrétní zápas |
| `ha_sport.refresh`, `ha_sport.test_notification` | |

Příklad (Vývojářské nástroje → Akce):
```yaml
action: ha_sport.get_matches
data:
  city: Brno
  status: upcoming
  days_ahead: 7
```

## Zdroj dat a upozornění

Data pochází z veřejného JSON API webu [Sofascore](https://www.sofascore.com) (neoficiální, bez API klíče).
Integrace požadavky omezuje: data ukládá do mezipaměti, kurzy stahuje jednou za 30 minut (oblíbené zápasy)
až 60 minut (ostatní), tabulky a pavouky jednou za hodinu, sestavy jen 90 minut před zápasem a rychlé obnovování
zapíná jen během zápasů. Volitelný druhý zdroj kurzů je [The Odds API](https://the-odds-api.com/) (vlastní API klíč).
Mládežnické a nižší soutěže SZĽH se čtou z webových stránek [HockeySlovakia.sk](https://www.hockeyslovakia.sk)
(tabulka jednou za hodinu, program a výsledky v běžném intervalu obnovy). Pokud je API dočasně nedostupné, zkouší se záložní adresy
a zobrazí se poslední známá data. Adresu API lze změnit v nastavení.

Odkazy na streamy vedou na oficiální platformy držitelů vysílacích práv. Kurzy jsou jen informativní.

Informace o vysílacích právech v sezóně 2025/26–2026/27 (použité pro odhad, když zdroj kanál neuvádí):
* Chance Liga – Oneplay Sport ([chanceliga.cz](https://www.chanceliga.cz/clanek/18361-z-kanalu-o2-tv-sport-se-stavaji-stanice-oneplay-sport-kde-se-bude-vysilat-chance-liga), [o2.cz](https://www.o2.cz/osobni/oneplay/chance-liga))
* Tipsport extraliga – Oneplay Sport + ČT sport ([hokej.cz](https://www.hokej.cz/z-kanalu-o2-tv-sport-se-stavaji-stanice-oneplay-sport-kde-se-od-pondeli-bude-vysilat-tipsport-extraliga/5087318))
* Niké liga – Voyo + Dajto ([nikeliga.sk](https://www.nikeliga.sk/clanok/3333-aj-v-novej-sezone-vsetky-zapasy-nike-ligy-nazivo-na-voyo))
* Tipsport liga (SK hokej) – JOJ Šport, JOJ Play ([7sport.sk](https://7sport.sk/hokej/kde-sledovat-tipsport-liga-nazivo/))
* NBL – ČT sport, TVCOM, TV Chance ([7sport.cz](https://7sport.cz/basketbal/nbl-basketbal/))
* Tipos SBL – JOJ Šport, Tipos TV ([7sport.sk](https://7sport.sk/basketbal/sbl-basketbalova-extraliga-muzov/))

## Řešení potíží

**Nevidím nové volby (soutěže SZĽH, odkaz na soutěž…)** – běží starší verze. Postupujte podle
[Aktualizace](#aktualizace) (Update information → Redownload → restart HA → Ctrl+F5).

**„Nelze se připojit ke zdroji dat (Sofascore)“** – za dvojtečkou je vypsaná přesná příčina pro každou zkoušenou adresu:

* `HTTP 403` – Sofascore odmítá klienty, kteří nevypadají jako prohlížeč. Integrace proto používá knihovnu
  [`curl_cffi`](https://github.com/lexiforest/curl_cffi), která se tváří jako Chrome. Home Assistant ji nainstaluje sám
  při prvním načtení integrace (po aktualizaci je nutný **restart HA**). Pokud 403 trvá, zkuste v poli *Adresa API*
  `https://api.sofascore.com/api/v1` nebo `https://api.sofascore.app/api/v1`. Některé VPN nebo IP adresy
  datacenter bývají blokované úplně.
* `... knihovna curl_cffi není nainstalovaná` – zkontrolujte log HA (*Nastavení → Systém → Protokoly*), proč se
  balíček nenainstaloval. Je k dispozici pro x86_64 a ARM64 (Raspberry Pi 4/5 s 64bitovým systémem).
* `ClientConnectorError` / `Timeout` – HA se nedostane na internet, případně DNS nebo firewall.

**Soutěž SZĽH nemá tabulku nebo zápasy** – parser hledá na stránkách HockeySlovakia.sk tabulky podle názvů sloupců.
Pokud svaz změní vzhled stránek, otevřete stránku tabulky nebo výsledků soutěže v prohlížeči, uložte ji
(Ctrl+S, „jen HTML“) a pošlete ji – parser se podle ní upraví. Chyba stahování je v logu HA
(`HockeySlovakia.sk: …`) a v atributu `szlh_error` senzoru **Poslední aktualizace**.

**Chybí kurzy** – podívejte se na atribut `odds` senzoru **Poslední aktualizace**:

* `with_odds` / `upcoming` – u kolika nadcházejících zápasů kurz je,
* `bookmakers` – které sázkové kanceláře se našly (pokud je jen `Sofascore`, zkuste zvýšit
  *Konfigurovat → Obecné → Počet sázkových kanceláří* nebo doplnit klíč The Odds API),
* `odds_api_error` / `odds_api_remaining` – chyba a zbývající dotazy The Odds API.

Sázkovky většinou vypisují kurzy až několik dní před zápasem, u vzdálenějších zápasů proto kurz chybět může.

## Vývoj

```bash
pip install -r requirements_test.txt
pytest tests tests_ha
```
`tests/` testují čistou logiku bez HA, `tests_ha/` celou integraci (config flow, entity, WebSocket, služby,
oznámení, kurzy z více zdrojů, detail zápasu) s mockovaným API.
