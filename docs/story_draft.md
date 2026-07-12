# Rascunho Narrativo - Capitulos 3, 4, 5 e Expansoes

Contexto de implementacao narrativa:
- RPG dark fantasy cooperativo para 2-4 jogadores.
- Um jogador e escolhido como lider da party e toma as decisoes finais.
- Classes com caminhos unicos: Guerreiro, Mago, Ladrao, Clerigo.
- Consequencias existentes: `ogro_poupado`, `goblin_ajudado`, `lacre_sombrio`, `elena_traiu`.
- Antagonista: Lorde Malakar, imortal enquanto 3 selos existirem.
- Tempo alvo: 1 hora para party de 3 jogadores.

## Expansao do Capitulo 1 - A Taverna do Inicio

### Cena de Abertura

A chuva cai grossa sobre a estrada real, transformando a noite em um borrão de lama, vento e relampagos distantes. A unica luz confiavel vem da Taverna do Inicio, uma construcao baixa de pedra e madeira onde viajantes sem destino se escondem do frio. Dentro dela, o fogo estala na lareira, canecas batem contra mesas gastas e cochichos morrem sempre que a porta se abre.

Naquela noite, quatro estranhos sao empurrados para o mesmo canto da taverna por uma sucessao de pressagios: corvos pousados no telhado, uma lua avermelhada atras das nuvens e o nome de Malakar sussurrado por gente que jura nunca ter ouvido falar dele. O taberneiro fecha as janelas com pressa e diz que nenhuma estrada esta segura. Se alguem quiser chegar a Oakhaven vivo, precisara viajar em grupo.

### Monologos de Classe

Guerreiro:
"Eu ja vi muralhas cairem e homens melhores do que eu desaparecerem na poeira. Ainda assim, uma lamina firme resolve problemas que oracoes e mapas nao resolvem."
"Se essa estrada quer sangue, que venha buscar o meu primeiro."

Mago:
"As estrelas estao desalinhadas. Ha uma forca antiga se movendo sob a terra, e ela nao se esconde mais de quem sabe ler seus sinais."
"Nao viajo por coragem. Viajo porque o conhecimento que ignoramos sempre volta como condenacao."

Ladrao:
"Estradas perigosas sao boas para dois tipos de gente: mortos e oportunistas. Eu prefiro continuar no segundo grupo."
"Se ha armadilhas, fechaduras ou mentiras no caminho, deixem comigo. So nao perguntem onde aprendi."

Clerigo:
"Toda chama sagrada treme antes de se apagar. Hoje, ate minha fe pareceu projetar sombra."
"Se Malakar e mesmo o nome por tras dessa escuridao, entao alguem precisa carregar luz ate onde ela nao quer entrar."

### Escolha do Lider

O taberneiro coloca uma moeda antiga sobre a mesa e diz que grupos sem voz unica morrem discutindo na primeira bifurcacao. Cada jogador vota em quem deve liderar a party. Em caso de empate, a moeda e lancada pelo taberneiro, mas ele avisa: "A moeda escolhe o rosto. O peso da escolha fica com todos."

O lider eleito recebe a palavra final em decisoes narrativas. Os demais personagens podem opinar antes de cada escolha importante, e suas classes ainda desbloqueiam caminhos unicos.

[Comentario de implementacao: registrar `party_lider` com o personagem escolhido. O lider decide opcoes finais, mas os class gates dependem da presenca da classe na party.]

## Capitulo 3 - Vila de Millhaven

### Entrada na Vila

A estrada para Millhaven abandona qualquer sinal de vida antes mesmo de chegar aos portoes. O vento sopra sem levantar folhas, como se ate a natureza evitasse tocar aquele lugar. Casas fechadas observam a party com janelas pregadas por dentro, e uma nevoa roxa escorre pelas ruas como agua suja. No centro da vila, o sino da capela balanca sozinho, mas nao emite som algum. A lua cheia parece grande demais sobre os telhados, branca como um olho doente. Nenhum cao late, nenhum bebe chora, nenhum aldeao se atreve a respirar perto das portas.

### Encontro com Padre Elias

A party encontra Padre Elias ajoelhado diante da capela. Ele e idoso, cego, vestido com panos brancos gastos, e segura um simbolo sagrado rachado. Apesar dos olhos esbranquiçados, ele vira o rosto exatamente na direcao da party.

Padre Elias: "A roda enfim rangeu ate minha porta. Entrem, viajantes. A noite ja pronunciou seus nomes."

Lider: "Voce nos conhece?"

Padre Elias: "Nao como homens conhecem rostos. Conheco voces como o sino conhece o vento: pelo peso que trazem."

Mago, se presente: "A vila esta sob maldicao. Que tipo de ritual causou isso?"

Padre Elias: "Ritual e palavra pequena. Isto e uma raiz. Foi plantada quando Veyr Malakar, o Nome Primeiro, recusou a morte e pediu ao vazio que lhe ensinasse a permanecer."

Clerigo, se presente: "Veyr Malakar e o nome verdadeiro dele?"

Padre Elias: "E o nome que ainda sangra. Lorde Malakar e a mascara; Veyr e o homem que queimou a propria alma para que a mascara nunca caisse."

Ladrao: "E por que essa mascara veio parar aqui?"

Padre Elias: "Porque Millhaven guardava um dos ecos do primeiro selo. Quando ele se aproximou, a vila ouviu o chamado e abriu as portas por dentro."

Guerreiro: "Diga onde esta o inimigo."

Padre Elias: "O inimigo esta no altar, na rua, no porao, no berco. Ele veste a pele dos lugares que desistiram de resistir."

Lider: "Ainda podemos salvar a vila?"

Padre Elias: "Uma vela ainda arde quando a cera ja chora. Salvem a crianca na casa do poço, e Millhaven talvez lembre como se respira."

Padre Elias: "Mas cuidado. O santo que a guarda caiu antes de voces chegarem. Agora ele marcha com a espada baixa e a aureola suja."

### Class Gate do Clerigo - A Crianca Corrompida

[Comentario de flag: se a party tiver Clerigo e escolher tentar a purificacao, abrir caminho para `millhaven_salva = True` apos a vitoria contra o Paladino Corrompido.]

A casa do poço fica no fim da rua principal. A porta esta aberta, mas nenhuma luz sai de dentro. No quarto superior, a party encontra uma crianca sentada no chao, de costas, cantando uma cantiga em uma lingua que nao deveria conhecer. A pele dela esta fria e marcada por veios roxos. Brinquedos quebrados giram lentamente ao redor, suspensos por uma forca invisivel.

Padre Elias sussurra da entrada: "Nao a firam. O mal a usa como lamparina."

O Clerigo sente a propria fe pesar no peito, como se uma mao gelada apertasse seu simbolo sagrado. Para purificar a crianca, ele precisa se ajoelhar no circulo de brinquedos e aceitar que parte da corrupcao tente entrar nele.

Clerigo: "Eu nao vim expulsar uma sombra com violencia. Vim lembrar esta casa de que ela ja teve amanhecer."

A crianca vira o rosto. Seus olhos sao negros, mas cheios de lagrimas.

Crianca: "Ele disse que, se eu dormir, meus pais voltam."

Clerigo: "Ele mentiu. Mas se voce acordar, nos ficamos ate o medo passar."

A nevoa roxa engrossa. Vozes imitam parentes mortos, prometendo descanso. O Clerigo ergue o simbolo rachado de Padre Elias e o proprio simbolo sagrado, juntando os dois como se fossem uma unica luz.

Clerigo: "Pela chama que resta nos lares vazios, pela mao que segura outra mao no escuro, pela vida que ainda nao aprendeu a se defender: saia dela."

A corrupcao explode em fios negros que tentam envolver o Clerigo. Os outros membros da party seguram portas, janelas e moveis enquanto a casa treme. O Clerigo perde forca, mas nao recua. Quando a luz finalmente atravessa o quarto, a crianca desaba chorando, viva, com os olhos humanos outra vez.

Padre Elias: "Millhaven ouviu. Ainda ha uma fresta."

Crianca: "O cavaleiro negro esta na capela. Ele disse que vai matar a luz que sobrou."

### Alternativa sem Clerigo

[Comentario de flag: se nao houver Clerigo, ou se a party recusar a purificacao, marcar `millhaven_perdida = True` apos o boss.]

Sem um Clerigo, a party tenta ajudar com palavras, agua limpa, fogo, magia ou forca de vontade. Nada firma. A crianca reconhece por um segundo que esta cercada por pessoas reais, mas a voz de Malakar fala por sua boca antes que alguem consiga alcanca-la.

Crianca Corrompida: "Tarde. A porta abriu por dentro."

A nevoa apaga a lamparina. Quando a luz volta, a crianca esta viva, mas seus olhos continuam negros. Ela nao ataca. Apenas volta a cantar, e cada nota faz as casas de Millhaven rangerem como caixoes sendo fechados.

Padre Elias: "Entao a vila esta perdida, mas nao deixem que sua perda seja inutil. Derrubem o guardiao caido. Levem adiante o que nao conseguimos salvar."

### Boss Fight Setup - Paladino Corrompido

Na capela, diante do altar, o Paladino Corrompido aguarda de joelhos. Sua armadura negra reflete a luz roxa das velas, e uma aureola quebrada gira atras do elmo como uma roda de ferro profanada. Quando ele se levanta, a espada negra raspa no piso sagrado.

Paladino Corrompido: "Eu protegi esta vila quando ainda havia vila para proteger."

Paladino Corrompido: "Rezei ate minha voz sangrar. O deus de Elias respondeu com silencio."

Paladino Corrompido: "Malakar me ofereceu uma verdade mais simples: tudo que se ajoelha pode ser possuido."

Paladino Corrompido: "Ajoelhem-se, ou aprendam como a fe soa quando quebra."

### Consequencias

Se a crianca foi purificada e o Paladino Corrompido derrotado:
[Comentario de flag: definir `millhaven_salva = True`. Nao definir `millhaven_perdida`. Aldeoes sobreviventes podem aparecer no Capitulo 4 e no Sistema de Aliados.]

Padre Elias toca o sino da capela. Desta vez ele soa baixo, rachado, mas real. Portas se abrem aos poucos. Millhaven nao celebra; apenas respira.

Se a crianca permaneceu corrompida:
[Comentario de flag: definir `millhaven_perdida = True`. Nao definir `millhaven_salva`. A vila permanece silenciosa e nao envia reforcos.]

A party deixa Millhaven sob a lua cheia. A cantiga da crianca continua atras deles por tempo demais, mesmo quando a vila ja desapareceu na nevoa.

## Capitulo 4 - O Cerco a Oakhaven

### Chegada Dramatica

O caminho de volta a Oakhaven esta marcado por cinzas. A cada colina vencida, o clarão no horizonte cresce, ate que a party percebe que nao e amanhecer: sao as muralhas queimando. Catapultas rugem alem dos campos, e sombras armadas se movem como uma maré escura contra os portoes. O sino de alerta toca sem ritmo, interrompido por gritos. Oakhaven, antes refugio, agora parece uma vela cercada por lobos.

### Encontro com Capita Rhea

Capita Rhea encontra a party perto do portao interno, com uma bandagem fresca atravessando a testa e sangue seco na armadura leve. Ela fala rapido, sem desperdiçar ar.

Rhea: "Vocês chegaram no pior momento possivel. O que, hoje, significa que chegaram na hora certa."

Lider: "Qual e a situacao?"

Rhea: "Tres frentes. Se uma cair, a cidade abre. Se duas cairem, Oakhaven vira cinza antes da meia-noite."

Guerreiro, se presente: "Aponte para onde a linha esta quebrando."

Rhea: "Portao Sul. Ogros de Malakar estao usando troncos como arietes. Meus soldados seguram por coragem, nao por força."

Mago, se presente: "E a fonte da barreira?"

Rhea: "Torre do Mago. A barreira antiga falha a cada impacto das catapultas. Se ela apagar, as flechas negras entram como chuva."

Ladrao, se presente: "Voce disse tres frentes. Qual delas esta quieta demais?"

Rhea: "O celeiro. Nossos suprimentos. Vi sombras entrando pelos fundos. Se perdermos comida e remedios, vencemos a noite e morremos na semana seguinte."

Clerigo, se presente: "E os feridos?"

Rhea: "No templo e nas ruas. Mas agora preciso impedir que a cidade inteira vire enfermaria."

Lider: "Nao podemos estar nos tres lugares ao mesmo tempo."

Rhea: "Nao precisam resolver tudo sozinhos. Escolham onde liderar. Suas classes podem virar o peso certo no lugar certo. Eu cobrirei o resto com quem ainda consegue ficar de pe."

Rhea: "Decidam rapido. O inimigo ja decidiu por nos."

### Frente 1 - Portao Sul

Classe ideal: Guerreiro.

Com Guerreiro:
O Guerreiro assume a linha de frente, pega o escudo quebrado de um soldado caido e finca os pes no barro diante do portao. Os ogros de Malakar avançam com troncos, mas a presenca de alguem capaz de receber o impacto reorganiza os defensores. A party cria um corredor de lanças, oleo e pedras. Quando o maior ogro investe, o Guerreiro o intercepta, quebra o ritmo do ariete e abre espaço para os guardas incendiarem o tronco.

Resultado narrativo: o Portao Sul resiste com baixas moderadas. Rhea ganha tempo para reposicionar arqueiros.

Sem Guerreiro:
Os soldados tentam segurar a linha sem um campeao fisico para ancorar a defesa. A party ajuda como pode, mas os ogros atingem o portao duas vezes antes de recuar. Parte da muralha racha, muitos defensores caem, e o combate seguinte começa com Oakhaven mais vulneravel.

Resultado narrativo: o Portao Sul resiste, mas com dano pesado e penalidade de recursos/vida para a proxima cena.

### Frente 2 - Torre do Mago

Classe ideal: Mago.

Com Mago:
O Mago sobe a torre sob chuva de brasas e encontra o cristal da barreira pulsando fora de ritmo. As runas antigas estao invertidas por interferencia sombria. Em vez de apenas despejar mana, o Mago le o padrao, corrige a sequencia e usa a propria energia como ponte temporaria. A barreira se reergue em placas azuladas, desviando flechas negras e pedras flamejantes.

Resultado narrativo: a barreira magica volta a funcionar. Catapultas inimigas perdem eficacia.

Sem Mago:
A party encontra aprendizes desesperados tentando manter o cristal vivo. Sem leitura arcana adequada, eles reforçam a torre manualmente e defendem os magos enquanto estes improvisam. A barreira volta por instantes, mas falha de novo sob impacto pesado.

Resultado narrativo: a cidade fica parcialmente protegida, mas projeteis continuam atingindo areas civis.

### Frente 3 - Celeiro

Classe ideal: Ladrao.

Com Ladrao:
O Ladrao percebe marcas finas na fechadura do celeiro e sinais de passagem no feno molhado. Em vez de entrar pela porta principal, guia a party pelo telhado baixo, surpreendendo sabotadores antes que acendam os barris de oleo. Ele corta pavios, trava a saida dos inimigos e transforma a emboscada deles em armadilha propria.

Resultado narrativo: suprimentos preservados. A cidade tera comida, remedios e flechas apos o cerco.

Sem Ladrao:
A party entra tarde demais. Os sabotadores sao derrotados, mas parte do celeiro pega fogo. Barris de grao e caixas de remedios queimam antes que os aldeoes apaguem as chamas.

Resultado narrativo: suprimentos parcialmente perdidos. Rhea menciona que a vitoria ficara mais cara.

### Consequencias Especiais

Se `ogro_poupado`:
Um rugido conhecido atravessa o campo de batalha. O Ogro Krug surge carregando uma roda de carroça como escudo e uma viga como clava. Soldados de Oakhaven quase disparam contra ele, mas a party o reconhece.

Krug: "Krug lembrar humano que poupou. Krug nao gostar homem de fogo."

Krug: "Hoje Krug bate em ogro errado. Depois Krug come. Primeiro bate."

Krug avança contra os ogros de Malakar e derruba um ariete sozinho, transformando panico em gritos de coragem.

Se `millhaven_salva`:
Quando o Portao Sul quase cede, aldeoes de Millhaven chegam com carroças, vigas e cordas. Estao pálidos, assustados, mas vivos.

Aldeao de Millhaven: "Voces nos deram uma manha. Viemos pagar com esta noite."

Os reforcos escoram o portao e carregam feridos para dentro.

### Boss - Inquisidor Sombrio

Depois que as tres frentes sao resolvidas, a praça central se apaga. As chamas ficam negras por um instante, e o Inquisidor Sombrio surge sobre os degraus da fonte, acompanhado por correntes que se movem como serpentes.

Inquisidor Sombrio: "Que belo teatro. Portoes salvos, torres erguidas, celeiros intactos. Voces confundem atraso com vitoria."

Rhea: "Voce nao tomara minha cidade."

Inquisidor Sombrio: "Sua cidade? Oakhaven ja foi pesada. So falta escolhermos a forma da queda."

Lider: "Entao venha cobrar pessoalmente."

Inquisidor Sombrio: "Com prazer. Malakar prefere herois quebrados ainda quentes."

Fase 1:
O Inquisidor usa correntes, fogo negro e invocacoes menores. Ele tenta separar a party e punir quem estiver ferido pelas frentes anteriores.

Transicao:
Ao perder metade da forca, ele apaga a propria tocha contra o peito. A armadura se abre em fissuras de luz negra, e as correntes prendem-se aos sinos da cidade.

Inquisidor Sombrio: "Ouçam. Cada sino e uma garganta. Eu so preciso ensinar Oakhaven a gritar."

Fase 2:
O Inquisidor usa os sinos como foco, causando ondas de medo e dano em area. Se a Torre do Mago foi protegida com sucesso, a barreira reduz parte do impacto. Se o Celeiro foi salvo, curas e flechas extras ajudam a manter a defesa.

Consequencia:
[Comentario de flag: ao derrotar o Inquisidor Sombrio e manter Oakhaven de pe, definir `oakhaven_defendida = True`.]

Rhea finca a espada no chao da praça e encara os sobreviventes.

Rhea: "Contem os vivos primeiro. Depois contaremos os mortos. Hoje Oakhaven nao caiu."

## Capitulo 5 - As Terras Corrompidas

### Paisagem

Apos Oakhaven, a estrada deixa de parecer estrada e se torna uma cicatriz. O solo das Terras Corrompidas e vermelho, rachado e quente, como se respirasse febre. Arvores carbonizadas se inclinam em direcao ao centro do dominio de Malakar, todas dobradas pelo mesmo vento que nao sopra em mais lugar nenhum. O ceu permanece sangrento mesmo quando deveria anoitecer, e cinzas caem devagar como neve suja. A agua nos buracos reflete rostos que nao pertencem a party. Ao longe, uma fortaleza negra parece mudar de lugar sempre que alguem pisca.

### Evento 1 - Acampamento de Sobreviventes

A party encontra um pequeno acampamento escondido atras de rochas vermelhas. Ha familias exaustas, um guarda ferido, duas criancas sem voz e uma mulher tentando cozinhar pedras em agua rala para fingir normalidade. O lider dos sobreviventes pede ajuda para atravessar um trecho patrulhado.

Escolha do lider: ajudar ou ignorar.

Se ajudar:
A party perde tempo desviando de patrulhas e carregando feridos. O ceu escurece mais cedo, e Malakar ganha terreno em sua preparacao final. Ainda assim, os sobreviventes chegam a um refugio de pedras antigas. Entre eles ha um arqueiro chamado Daren, que promete guiar mensageiros e espalhar alertas.

Sobrevivente: "Achei que herois fossem historias para quem ainda tinha casa. Obrigado por provar que eu estava errado."

Resultado narrativo: a party ganha um aliado logistico para o final, mas chega mais cansada ao proximo evento.

Se ignorar:
O lider decide que a missao e urgente demais. A party segue, ouvindo os pedidos ficarem menores atras do vento. Horas depois, encontra sinais de luta e uma fita infantil presa a um galho queimado.

Resultado narrativo: a party economiza tempo, mas carrega culpa. Theron pode mencionar que poucos sobrevivem sem ajuda nessas terras.

### Evento 2 - Santuario Profanado

A party encontra um santuario quebrado, semi-enterrado em cinzas. Tres pilares cercam um mosaico destruido. No centro, uma figura coroada aparece ajoelhada diante de um abismo pintado em tinta preta.

Com Mago:
O Mago reconhece que as runas nao foram feitas para louvar Malakar, mas para aprisionar a historia dele. Ao tocar o mosaico, a memoria do santuario acorda.

Revelacao completa:
Veyr Malakar foi um campeao de uma ordem antiga que protegia as fronteiras entre o mundo mortal e o Vazio Profundo. Quando sua cidade natal foi destruida por uma praga, ele implorou aos deuses por tempo para desfazer a perda. Recebeu silencio. Entao desceu ao Vazio e fez um acordo com aquilo que nao possuia nome: ele preservaria sua existencia dividindo a propria morte em tres selos.

O primeiro selo foi cravado no sangue: uma linhagem inocente marcada para sustentar sua carne. Esse eco apareceu em Millhaven.

O segundo selo foi cravado na fe: um juramento guerreiro corrompido para sustentar sua vontade. Esse eco marchou como o Paladino Corrompido.

O terceiro selo foi cravado na chama: um portal entre mundo e Vazio para sustentar sua alma. Esse selo aguarda no templo final.

Enquanto os tres selos existirem, Malakar pode ser ferido, derrotado e ate destruido por instantes, mas sempre retornara. Para mata-lo, a party precisa quebrar os ecos dos selos e enfrentar sua forma final diante do portal.

Mago: "Ele nao escapou da morte. Ele a espalhou em lugares onde outros pagariam o custo."

Sem Mago:
A party encontra apenas ruinas, mosaicos quebrados e runas ilegíveis. O sentido se perde. Eles percebem que Malakar e antigo e que o santuario tentou esconder algo sobre ele, mas nao descobrem os detalhes dos tres selos.

Resultado narrativo: Theron ainda revela as fases de Malakar depois, mas com menos clareza e mais incerteza.

### Evento 3 - Emboscada de Assassinos

Com Ladrao:
O Ladrao nota que o vento parou de carregar cinzas em um trecho estreito. Ha fios finos entre as pedras, marcas de botas leves e um corvo morto posicionado como aviso falso. Ele sinaliza silencio e guia a party para fora da trilha aparente.

Os assassinos de Malakar esperam onde a party deveria passar. O Ladrao chega por tras, corta a corda da primeira armadilha e coloca uma adaga contra a mascara de osso do lider inimigo.

Ladrao: "Boa escolha de sombra. Ma escolha de alvo."

A party inicia o combate em vantagem, surpreendendo os assassinos e evitando dano inicial.

Sem Ladrao:
A party atravessa o corredor de pedra sem perceber os fios. Dardos negros disparam das laterais, fumaça cobre o caminho e assassinos mascarados caem de cima com adagas duplas.

Resultado narrativo: a emboscada ativa. A party sofre dano inicial antes do combate.

### Se `lacre_sombrio`

Durante a noite, a marca do Lacre Sombrio esquenta como metal no fogo. A paisagem desaparece, e a party se ve em um salao sem paredes, sob um ceu cheio de olhos brancos. Malakar fala sem mover labios, sua voz saindo de dentro das proprias lembrancas dos personagens.

Malakar: "Voces carregam uma lasca da porta que fingem querer fechar."

Malakar: "Sentem? Ela nao pesa. Ela reconhece. O Lacre sabe que voces ja aceitaram usar trevas quando a luz era lenta demais."

Malakar: "Nao condeno isso. Pelo contrario, admiro. Herois honestos morrem cedo; os uteis aprendem a mentir para si mesmos."

Malakar: "Venham ate mim com esse poder intacto, e eu lhes darei um mundo sem perdas. Nao um mundo bom. Bondade e fragil. Darei um mundo obediente."

Malakar: "Continuem resistindo, e cada aliado que conquistaram sera apenas mais uma voz me pedindo para faze-los parar."

Quando a visao termina, a party esta de pe no mesmo lugar, mas todos sentem que deram um passo em direcao ao templo sem mover os pes.

### Se `elena_traiu`

Elena aparece entre duas arvores carbonizadas, usando vestes rasgadas por energia roxa. Ela nao surge como monstro. Surge como alguem que chorou ate nao restar nada alem da decisao.

Elena: "Eu esperei odiar voces. Teria sido mais facil."

Lider: "Elena, nao precisa terminar assim."

Elena: "Nao? Voces tomaram poder proibido, esconderam verdades, escolheram atalhos. Malakar so terminou a frase que voces começaram."

Mago, se presente: "Ele esta usando sua dor."

Elena: "E voces usaram minha confiança."

Clerigo, se presente: "Ainda ha caminho de volta."

Elena: "Para mim, talvez. Para quem eu fui, nao."

Ela ergue as maos, e magia corrompida forma laminas de luz roxa. O confronto deve ser emocional: Elena hesita ao atingir membros que foram gentis com ela, mas fica mais agressiva se o lider tenta justificar escolhas sombrias. Ao ser derrotada, ela cai de joelhos.

Elena: "Se vencerem... provem que eu estava errada. Por favor."

Resultado narrativo: mini-boss opcional antes de Theron. A cena reforca a consequencia de `elena_traiu`.

### Encontro com Theron

Theron surge de uma fenda entre rochas, apontando uma tocha tremula para a party. Esta maltrapilho, magro, com olhos de quem viu o fim e continuou andando por engano.

Theron: "Nao deem mais um passo se ainda gostam dos proprios nomes."

Lider: "Quem e voce?"

Theron: "Theron. Fui guia de uma expedição. Fui marido. Fui covarde. A ordem muda dependendo da noite."

Guerreiro, se presente: "Voce viu Malakar?"

Theron: "Vi o que ele deixa os vivos lembrarem. Ja e demais."

Mago, se presente: "Sabe como ele luta?"

Theron: "Tres vezes. Ele mata tres vezes porque morreu dividido em tres."

Clerigo, se presente: "Explique."

Theron: "Primeiro vem o rei de armadura: espada, sombra, orgulho. Ele testa se voces sao fortes."

Theron: "Depois vem o feiticeiro do Vazio: correntes, fogo roxo, palavras dentro da cabeça. Ele testa se voces sao inteiros."

Theron: "Por fim vem o que sobrou do homem Veyr Malakar. Sem coroa. Sem pele de lenda. So fome, portal e medo da morte. Essa e a fase que ninguem sobreviveu para descrever direito."

Ladrao, se presente: "Mas voce sobreviveu."

Theron: "Eu corri antes da terceira porta abrir. Ou talvez ele me deixou correr para contar a voces. Nao sei qual resposta me assusta mais."

Lider: "Como chegamos ao portal?"

Theron: "Pelo Guardiao. Pedra e sombra. Sem rosto. Ele nao protege Malakar. Protege a ideia de que Malakar pode voltar."

Theron: "Quando ele cair, nao esperem descanso. Portais nao gostam de ficar abertos, e o Vazio odeia perder propriedade."

### Boss - Guardiao do Portal

O Guardiao do Portal se ergue diante de um arco colossal partido ao meio. Seu corpo e feito de rochas antigas suspensas por sombra liquida, com runas brilhantes pulsando onde deveria haver juntas. Nao possui rosto, apenas uma cavidade escura que parece puxar a luz para dentro. Cada passo dele faz o chao lembrar terremotos antigos.

Guardiao do Portal: "Nenhum mortal passa inteiro."

Guardiao do Portal: "Entreguem carne, memoria e nome. O portal decidira o que resta."

Resultado narrativo: ao derrotar o Guardiao, a party acessa o templo final e as tres salas antes de Malakar.

## Expansao do Capitulo 6 - Tres Salas Antes de Malakar

### Sala dos Enigmas

A primeira sala e circular, coberta por espelhos de obsidiana. No centro, uma estatua sem rosto segura tres chaves: uma de osso, uma de ferro e uma de vidro. Uma inscricao aparece no chao quando a party entra.

Enigma:
"Sou porta quando fechado,
prisao quando aberto,
promessa quando quebrado.
Reis me usam para mentir,
mortos me usam para ficar.
O que sou?"

Resposta esperada: "selo".

Com Mago:
O Mago percebe que a resposta nao deve ser falada em voz alta, mas escrita com mana no ar. Ao formar a palavra "selo", os espelhos mostram os tres fragmentos da imortalidade de Malakar: sangue, fe e chama. A chave de vidro se desfaz, revelando a passagem.

Mago: "Ele construiu a eternidade como uma fechadura. Toda fechadura aceita uma resposta."

Sem Mago:
A party tenta responder verbalmente ou escolher uma chave. A sala interpreta hesitacao como erro. Os espelhos disparam estilhaços de sombra, causando dano e aplicando medo. A porta abre apenas depois que a party força a passagem, pagando o custo.

### Sala dos Mortos

A segunda sala parece uma cripta sem fim. Nichos nas paredes guardam corpos de antigos defensores, todos com as maos amarradas por fios roxos. Quando a party avança, os mortos levantam a cabeça ao mesmo tempo.

Com Clerigo:
O Clerigo entende que aqueles mortos nao querem lutar; estao presos ao terceiro selo como sentinelas involuntarios. Ele coloca o simbolo sagrado no chao e chama cada morto nao por nome, mas por direito.

Clerigo: "Vocês ja deram o ultimo folego. Nenhum tirano pode exigir o seguinte."

As amarras roxas queimam em luz branca. Um por um, os mortos abaixam as armas. Alguns sussurram agradecimentos sem voz. A cripta abre passagem, e uma benção temporaria protege a party contra medo no confronto final.

Sem Clerigo:
Os mortos-vivos despertam completamente. Eles nao gritam, nao ameaçam, apenas atacam com a obediencia triste de quem foi impedido de descansar. A party precisa lutar contra antigos defensores antes de seguir, gastando recursos.

### Sala do Silencio

A terceira sala nao produz som. Passos, respiracao e metal ficam mudos. Ha um cofre negro no centro, ligado por fios quase invisiveis a sinos, laminas e placas de pressao nas paredes. Dentro dele esta um foco de energia capaz de enfraquecer a primeira fase de Malakar.

Com Ladrao:
O Ladrao sente o silencio como uma armadilha, nao como paz. Ele usa farinha, cinza ou poeira para revelar os fios, marca placas soltas no chao e trabalha na fechadura sem ouvir o proprio metal. O mecanismo exige paciencia: primeiro travar o sino, depois prender a lamina, por fim girar a fechadura no intervalo entre dois pulsos de luz roxa.

Quando o cofre abre, o som retorna em uma pancada de ar. Dentro ha um fragmento frio de corrente negra.

Ladrao: "Silencio demais sempre esta escondendo alguem que quer ouvir voce morrer."

Resultado narrativo: a party obtem vantagem contra Malakar, como reduzir escudo inicial ou impedir uma invocacao.

Sem Ladrao:
A party identifica tarde demais que o cofre esta conectado a armadilhas. Tentar abrir seria arriscado demais, ou dispara uma lamina que obriga todos a recuar. O cofre permanece fechado.

Resultado narrativo: sem vantagem adicional para o confronto final.

## Sistema de Aliados - Chegada ao Templo

Antes da entrada final, a party encontra a escadaria do templo cercada por vento roxo. Quando parece que subirao sozinhos, vozes surgem atras deles.

Se `ogro_poupado`:
Krug aparece carregando uma pedra enorme no ombro, como se fosse equipamento de viagem.

Krug: "Krug veio. Krug prometeu ajudar."

Krug: "Homem de coroa ruim machuca pequenos. Krug quebra caminho. Amigos sobem."

Se `goblin_ajudado`:
Zix salta de tras de uma coluna quebrada, ofegante, com uma mochila cheia de coisas roubadas dos inimigos.

Zix: "Zix achou voces! Zix tambem achou entrada pequena, corda boa e queijo ruim."

Zix: "Humanos salvaram Zix. Agora Zix salva humanos um pouquinho. Talvez muito."

Se `millhaven_salva`:
Um aldeao de Millhaven se aproxima com outros sobreviventes, carregando lanternas cobertas por panos.

Aldeao: "Nossa vila ainda respira por causa de voces. Nao podemos lutar como herois, mas podemos manter a escuridao longe da porta."

Se `oakhaven_defendida`:
Capita Rhea chega com soldados marcados por fuligem, mas firmes.

Rhea: "Oakhaven ficou de pe. Agora ela marcha ate onde a guerra começou."

Rhea: "Entrem no templo. Nos seguraremos qualquer coisa que tente sair atras de voces."

[Comentario de implementacao: aliados nao precisam acompanhar o combate final inteiro. Eles podem fornecer bonus narrativos, reducao de penalidades, itens, protecao contra emboscadas ou cenas de suporte antes das salas finais.]

## Confronto Final com Malakar - Dialogo Adicional da Fase 3

Na terceira fase, a armadura de Malakar se parte. A coroa de espinhos cai no chao e queima sem fogo. O que resta diante da party nao parece um deus sombrio, mas um homem antigo sustentado por odio demais para morrer. Atrás dele, o portal pulsa como um coracao doente.

Malakar: "Eu dei seculos ao mundo. Ordem. Medo. Continuidade."

Lider: "Voce deu correntes."

Malakar: "Correntes seguram pontes. Seguram reinos. Seguram pessoas longe do abismo que fingem nao desejar."

Se `lacre_sombrio`:
O Lacre Sombrio reage ao portal. A luz roxa envolve a party, e Malakar sorri pela primeira vez sem fingir grandeza.

Malakar: "Ai esta. O poder que voces juraram controlar."

Malakar: "O pergaminho nao corrompe. Ele traduz. Ele mostra o que a alma pediria se nao temesse testemunhas."

Malakar: "Usem-no. Quebrem o portal com minha propria lingua. Salvem todos do jeito que eu salvaria."

Clerigo, se presente: "Isso nao e salvacao."

Malakar: "Salvacao e o nome que os vencedores dao ao metodo que sobreviveram para defender."

Mago, se presente: "Se usarmos isso, continuamos o ciclo."

Malakar: "Ciclos sao apenas eternidade vista por olhos pequenos."

Ladrao, se presente: "Voce fala demais para alguem com medo."

Malakar: "Tenho medo, sim. Foi por isso que venci a morte. Coragem e uma virtude inventada por mortais sem alternativa."

Guerreiro, se presente: "Entao morra com medo."

Malakar: "Tentem."

[Comentario de implementacao: se `lacre_sombrio` estiver ativo, oferecer escolha final ao lider: usar o poder sombrio para ganhar vantagem com custo narrativo, ou rejeitar o lacre e enfrentar Malakar sem esse poder. A escolha deve influenciar o final.]
