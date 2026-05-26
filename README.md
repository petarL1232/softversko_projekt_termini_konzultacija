# Semestralni projekt - stranica za upravljanje terminima za labaratorij

### Stack:
- Python 3.11+
- FastAPI + Uvicorn
- PostgreSQL
- SQLModel
- pytest
- ruff + black
- Docker / docker-compose
- bcrypt za password hashing
- minimalni HTML/CSS/JS UI

# Skok na sekcije

- [Docker](#pokretanje-s-dockerom)
- [Pregled web stranice](#pregled-web-stranice)
  - [Student](#prijava-kao-student)
  - [Administrator](#prijava-kao-administrator)
- [API](#api) 
- [Demo scenarij](#demo-scenarij)

## Pokretanje s Dockerom

Prije pokretanja projekta, potrebno je ispuniti `.env` datoteku. 
Funkcionalan primjer postoji u `.env.example` datoteci.

Nakon toga, najjedostavniji način za pokretanje projekta je uz pomoć `docker compose up --build -d`.

Aplikacija se zatim otvara na: 
```
http://localhost:800
```

### Development

Testovi se lokano pokreću uz pomoć `pytest`. Na Github repozitoriju je također prisutan **Github Actions** koji automatski na svaki commit/push pokreće testove.

Za lint i formatiranje se koristi `ruff check .` i `black .`

# Pregled web stranice

U ovom demo-u, moguće je prijaviti se kao student, kao admin ili registrirati vlastiti račun.

## Prijava kao student

Nakon prijave, moguće je vidjeti:

### Moje prijave

Sekcija koja prikazuje termine na koje je korisnik trenutno prijavljen, zajedno uz datum i vrijeme termina. 

Ako korisnik ima prijavljene termine, ova sekcija omogućuje i brzu odjavu s tog termina.

### Termini konzultacija

Sekcija koja prikazuje trenutno dostupne termine i omogućuje prijavu na termine.

Pri vrhu je **pretraga termina** koja omogućuje pretragu preko **ID-a profesora** ili preko **ID-a predmeta**, uz još moguće filtre za samo slobodne termine ili samo korisnikove termine.

Nakon pretrage, vidljive su kartice koje prikazuju naziv termina, ID profesora i predmeta, datum i vrijeme termina, popunjenost i gumb za prijavu/odjavu termina.
Kartica, naravno, prikazuje i jeli korisnik prijavljen na taj termin ili ne.

## Prijava kao administrator

Ova demo stranica podržava i mogućnosti administratora nad terminima.

Pri vrhu stranice je vidljiva sekcija za health provjeru stranice i gumb za `Swagger` dokumentaciju API-a. Više o ovome u [API sekciji](#api). 

Nakon toga je vidljivo da je korisnik prijavljen kao administrator, uz gumb za odjavu.

Zatim slijedi sekcija za **upravljanje terminima**.

Prvobitno, moguće je osviježiti dostupne termine i **kreirati novi termin**. Klikom na gumb novi termin otvara se unos za ID profesora i predmeta, početni i završni datum. Važno je spomenuti da za unos datuma se koristi drop-down kalendar.

Nakon eventualnog unosa novog termina, vidljivi su svi termini zajedno sa svim njihovim relevantnim podatcima, gdje je moguće **urediti** i **izbrisati** pojedini termin.

Na kraju se nalazi sekcija za upravljanje svim korisnicima na stranici. 
Ovdje je moguće promijenizi office ID i ulogu svakog korisnika: student, profesor ili admin.

# API

Swagger dokumentacija je vidljiva na `http://localhost:8000/docs`.

## Trenutni endpoint-i:

### Auth:

- [GET /auth/users](http://localhost:8000/docs#/auth/list_users_auth_users_get)
- [PATCH /auth/users/{user_id}/role](http://localhost:8000/docs#/auth/update_user_role_auth_users__user_id__role_patch)
- [POST /auth/register](http://localhost:8000/docs#/auth/register_user_auth_register_post)
- [POST /auth/login](http://localhost:8000/docs#/auth/login_user_auth_login_post)
- [GET /auth/me](http://localhost:8000/docs#/auth/read_me_auth_me_get)

### Termini:

- [GET /termini](http://localhost:8000/docs#/termini/list_termini_termini_get)
- [POST /termini](http://localhost:8000/docs#/termini/create_termin_termini_post)
- [GET /termini/popunjenost/{termin_id}](http://localhost:8000/docs#/termini/popunjenost_termina_termini_popunjenost__termin_id__get)
- [GET /termini/{termin_id}](http://localhost:8000/docs#/termini/get_termin_termini__termin_id__get)
- [PUT /termini/{termin_id}](http://localhost:8000/docs#/termini/update_termin_termini__termin_id__put)
- [DELETE /termini/{termin_id}](http://localhost:8000/docs#/termini/delete_termin_termini__termin_id__delete)

### Prijave:

- [POST /termini/{termin_id}/prijava](http://localhost:8000/docs#/termini/delete_termin_termini__termin_id__delete)
- [DELETE /termini/{termin_id}/prijava](http://localhost:8000/docs#/prijave/odjavi_se_s_termina_termini__termin_id__prijava_delete)
- [GET /me/prijave](http://localhost:8000/docs#/prijave/moje_prijave_me_prijave_get)
- [GET /termini/{termin_id}/popunjenost](http://localhost:8000/docs#/prijave/popunjenost_termina_termini__termin_id__popunjenost_get)

### System:
- [GET /health](http://localhost:8000/docs#/system/health_health_get)

# Demo scenarij

TBD
