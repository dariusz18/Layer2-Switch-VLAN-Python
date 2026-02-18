1 2

Deciziile de design au fost: 
-Tabela MAC ca dictionar Python
-Lista dest_ports[], verificare VLAN pe fiecare port
-Separarea functiilor

ex1.png : Se observa
-ping urile intre host uri
-wireshark cu trafic icmp
-switch urile care ruleaza

ex2.png : Se observa
-ping host0 → host2 (ambele VLAN 1): SUCCESS (0% loss)
-ping host0 → host1 (VLAN 1 → VLAN 2): FAIL (100% loss)
-wireshark cu pachetel icmp


Implementare : 
Task 1 :

Tabela de comutare: MAC_Table - dictionar Python
-Cheie: MAC (bytes)
-Valoare: port (int)
-Algoritm:
-La primire: MAC_Table[src_mac] = port
-La forwarding:
-Unicast + destinatie cunoscuta → trimite pe portul din tabela
-Altfel → flooding (toate porturile exceptand sursa)
-Functia is_unicast() verifica primul bit MAC


Task2 : 
-port{} - mapare interfata → VLAN ID
-trunk{} - interfata este trunk? (True/False)
Functii:
-create_vlan_tag() - creeaza tag VLAN
-get_exit_id_mac() - calculeaza extended ID din MAC
-same_vlan() - verifica VLAN pentru broadcast
-same_vlan_extended() - verifica VLAN + extended ID pentru unicast
-send_frame() - adauga/elimina tag

Logica:
-La primire: extrag VLAN ID (din tag sau config)
-La forwarding:
-Trunk → pastreaza/adauga tag (0x8200)
-Access → elimina tag
-Verificare izolare:
-Unicast → VLAN ID + extended ID
-Broadcast → doar VLAN ID
Extended ID = suma nibble-urilor MAC (ultimi 4 biti)


Dificultati : -> Cand sa aplic extended VLAN ID?
Solutie: doar pentru unicast cu destinatie cunoscuta

Autoevaluare : - Codul este functional si corect, dar lipsesc optimizari de performanta
- Nu am facut taskul 3 => am fost nevoit sa hardcodez blocarea interfetei rr-0-2 pe Switch2 pt a elimina bucla din topologie# Layer2-Switch-VLAN-Python
