# 10｜承重引文德文级核验报告

- **车道**：A2A 网络「顾权席」文献核验子代理（德文原文层）
- **日期**：2026-10-11（核验执行跨 2026-10-08 至 10-11；网络源多轮重试）
- **任务**：对综合稿 `00_synthesis.md` 未决项 1 与 4 登记的证据强度不对称做闭环——03/09 两稿的尼采/康德承重引文此前仅走公版英译（+个别德文），本轮对 8 条承重引文逐条补德文原文层核验。
- **铁律执行**：每条给出德文原文照抄（逐字，含旧正字法）+ 出处 URL + 章节 + 与英译/中译主张的对照判定（一致/偏差/误译/未检得）；找不到原文即标「未检得」，不从记忆补写。

---

## 判定速览

| # | 引文 | 判定 |
|---|---|---|
| 1 | GM I §10 怨恨创造价值段 | **未检得**（德文源不可达，见该节） |
| 2 | GM I §2 Pathos der Distanz 段 | **未检得**（德文源不可达，见该节） |
| 3 | JGB §211 发令者与立法者 | **一致** |
| 4 | JGB §260 Herren-Moral 命名段 | **一致** |
| 5 | Za I:15 人类自予善恶 | **一致**（附措辞提示：委托方德文意写与原文不符） |
| 6 | Za II:12 生命自白自我超越 | **一致** |
| 7 | GMS 4:432 自律公式 | **未检得**（德文源不可达，见该节） |
| 8 | 《何谓启蒙》8:35 座右铭段 | **一致**（并证伪「ungestaltetes Vieh」误记） |

**总判：一致 5 条（#3/4/5/6/8）；偏差 0 条（英译主张 vs 德文）；未检得 3 条（#1/2/7）。**

---

## 1. GM I §10——「怨恨本身变得能产并生出价值」

**英译主张**（09 §2.3 引，Samuel 译 PG #52319，原标「指针级，未读全章」）：
> "The revolt of the slaves in morals begins in the very principle of resentment becoming creative and giving birth to values."

委托方提示的德文对应句：「das Sklaven-Aufstand in der Moral beginnt damit, dass der Ressentiment selbst schöpferisch wird und Werte erschafft」。

**德文原文**：**未检得**。本轮未能从任何可访问德文源照抄原文，按铁律不凭记忆补写。

**尝试记录（全部失败）**：
- `https://www.projekt-gutenberg.org/nietzsch/genealog/genealog1.html`（Gutenberg-DE GM 第一篇）——FetchURL 4 次均 403（Cloudflare）；curl 命中 Cloudflare JS 验证页；同站 `genealog.html`（GM 前言）2 次成功，唯正文页被闸。
- `https://www.gutenberg.spiegel.de/`（spiegel 系镜像）——网络不可达（curl 超时/FetchURL network error）。
- `https://de.wikisource.org/` GM 各页——network error（连域名级搜索页亦失败）。
- `https://web.archive.org/` Wayback 存档——network error。
- Project Gutenberg（gutenberg.org）德文库逐号探测：#7203=Götzen-Dämmerung、#7204=JGB、#7205=Za；站内检索 "genealogie der moral" 仅返回英译本 #52319。**PG 无 GM 德文本**。
- `https://www.deutschestextarchiv.de/nietzsche_genealogie_1887`（DTA 1887 首版）——JS cookie 验证闸，curl 不可过；浏览器通道当时不可用。
- `https://www.textlog.de/nietzsche-genealogie.html`——站点已改为 JS 应用壳，无文本。

**对照判定**：**未检得**。英译主张的德文措辞对应关系本轮无法证成；03/09 原标注的「英译级已核、德文未核」状态维持。

**置信说明**：失败模式为网络/反爬层（Cloudflare 403、JS 验证、整站不可达），非「文本不存在」。GM I §10 德文在 KSA 5.264–265 / projekt-gutenberg 正文页均有公开文本，待通路恢复后可一键闭环。委托方给出的德文提示句中冠词疑有误（通行作 "Der Sklavenaufstand… das Ressentiment…"），亦待原文照抄后定谳，本轮不预断。

---

## 2. GM I §2——「距离的激情」与「好」的自我设定

**英译主张**：GM 第一篇 §2 中「Pathos der Distanz」段及「好=高贵者自我设定」论证（03 §2 差异表、09 §2 相关论证的隐含地基；综合稿引证链指向 GM I §2）。

**德文原文**：**未检得**。失败模式与第 1 条完全相同（同一书籍正文页），不重述。

**对照判定**：**未检得**。

**置信说明**：同上——属通路问题而非文本不存在问题。恢复 projekt-gutenberg 正文页或 KSA 通路后即补。

---

## 3. JGB §211——「发令者与立法者」

**英译主张**（03 §2.1(e)、09 §2.1，Zimmern 译 PG #4363，原标「本轮读原文核实」）：
> "…his task itself requires him TO CREATE VALUES… THE REAL PHILOSOPHERS, HOWEVER, ARE COMMANDERS AND LAW-GIVERS; they say 'So shall it be!'… Their 'knowing' is CREATING, their creating is a law-giving, their will to truth is—WILL TO POWER."

**德文原文照抄**（PG 德文纯文本逐字，旧正字法保留）：

> «diese Aufgabe selbst will etwas Anderes, - sie verlangt, dass er Werthe schaffe. Jene philosophischen Arbeiter nach dem edlen Muster Kant's und Hegel's haben irgend einen grossen Thatbestand von Werthschätzungen - das heisst ehemaliger Werthsetzungen, Werthschöpfungen, welche herrschend geworden sind und eine Zeit lang "Wahrheiten" genannt werden - festzustellen und in Formeln zu drängen, sei es im Reiche des Logischen oder des Politischen (Moralischen) oder des Künstlerischen. Diesen Forschern liegt es ob, alles bisher Geschehene und Geschätzte übersichtlich, überdenkbar, fasslich, handlich zu machen, alles Lange, ja "die Zeit" selbst, abzukürzen und die ganze Vergangenheit zu überwältigen: eine ungeheure und wundervolle Aufgabe, in deren Dienst sich sicherlich jeder feine Stolz, jeder zähe Wille befriedigen kann. **Die eigentlichen Philosophen aber sind Befehlende und Gesetzgeber: sie sagen "so soll es sein!", sie bestimmen erst das Wohin? und Wozu? des Menschen und verfügen dabei über die Vorarbeit aller philosophischen Arbeiter, aller Überwältiger der Vergangenheit, - sie greifen mit schöpferischer Hand nach der Zukunft, und Alles, was ist und war, wird ihnen dabei zum Mittel, zum Werkzeug, zum Hammer. Ihr "Erkennen" ist Schaffen, ihr Schaffen ist eine Gesetzgebung, ihr Wille zur Wahrheit ist - Wille zur Macht.** - Giebt es heute solche Philosophen? Gab es schon solche Philosophen? Muss es nicht solche Philosophen geben?...»

**出处**：Friedrich Nietzsche, *Jenseits von Gut und Böse*, Project Gutenberg eBook **#7204（德文）**，https://www.gutenberg.org/cache/epub/7204/pg7204.txt ；第六章「Wir Gelehrten」内 §211（文本内编号 "211."，其后即 "212."，节号经文本内编号确认）。本地快照行 4276–4298。

**对照判定**：**一致**。
- "COMMANDERS AND LAW-GIVERS" ↔ «Befehlende und Gesetzgeber»；
- "'So shall it be!'" ↔ «"so soll es sein!"»；
- "TO CREATE VALUES" ↔ «Werthe schaffe»；
- "'knowing' is CREATING" ↔ «"Erkennen" ist Schaffen»；
- "creating is a law-giving" ↔ «Schaffen ist eine Gesetzgebung»；
- "will to truth is—WILL TO POWER" ↔ «Wille zur Wahrheit ist - Wille zur Macht»。

**置信说明**：高。德文为 PG 公版德文全本逐字照抄；03/09 的中译转述（「真正的哲学家却是命令者与立法者……他们的『知』是创造，他们的创造是立法，他们的真理意志是——权力意志」）与德文逐词对应，无走样。

---

## 4. JGB §260——「Herren-Moral und Sklaven-Moral」命名段

**英译主张**（09 §2.2 命名段 + §4.2 解毒剂段，Zimmern 译）：
> 命名：「Es giebt Herren-Moral und Sklaven-Moral」（"There is master-morality and slave-morality"）；
> 解毒剂：「the noble man also helps the unfortunate, but not—or scarcely—out of pity, but rather from an impulse generated by the super-abundance of power」；「takes pleasure in subjecting himself to severity and hardness」。

**德文原文照抄**（PG 德文纯文本逐字）：

> «Bei einer Wanderung durch die vielen feineren und gröberen Moralen, welche bisher auf Erden geherrscht haben oder noch herrschen, fand ich gewisse Züge regelmässig mit einander wiederkehrend und aneinander geknüpft: bis sich mir endlich zwei Grundtypen verriethen, und ein Grundunterschied heraussprang. **Es giebt Herren-Moral und Sklaven-Moral;** - ich füge sofort hinzu, dass in allen höheren und gemischteren Culturen auch Versuche der Vermittlung beider Moralen zum Vorschein kommen, noch öfter das Durcheinander derselben und gegenseitige Missverstehen, ja bisweilen ihr hartes Nebeneinander - sogar im selben Menschen, innerhalb Einer Seele. Die moralischen Werthunterscheidungen sind entweder unter einer herrschenden Art entstanden, welche sich ihres Unterschieds gegen die beherrschte mit Wohlgefühl bewusst wurde, - oder unter den Beherrschten, den Sklaven und Abhängigen jeden Grades. Im ersten Falle, wenn die Herrschenden es sind, die den Begriff gut- bestimmen, sind es die erhobenen stolzen Zustände der Seele, welche als das Auszeichnende und die Rangordnung Bestimmende empfunden werden. Der vornehme Mensch trennt die Wesen von sich ab, an denen das Gegentheil solcher gehobener stolzer Zustände zum Ausdruck kommt: er verachtet sie. Man bemerke sofort, dass in dieser ersten Art Moral der Gegensatz "gut" und "schlecht" so viel bedeutet wie "vornehm" und "verächtlich": - der Gegensatz "gut" und "böse" ist anderer Herkunft.»

> «Die vornehme Art Mensch fühlt sich als werthbestimmend, sie hat nicht nöthig, sich gutheissen zu lassen, sie urtheilt "was mir schädlich ist, das ist an sich schädlich", sie weiss sich als Das, was überhaupt erst Ehre den Dingen verleiht, sie ist wertheschaffend. … **auch der vornehme Mensch hilft dem Unglücklichen, aber nicht oder fast nicht aus Mitleid, sondern mehr aus einem Drang, den der Überfluss von Macht erzeugt.** **Der vornehme Mensch ehrt in sich den Mächtigen, auch Den, welcher Macht über sich selbst hat, der zu reden und zu schweigen versteht, der mit Lust Strenge und Härte gegen sich übt** und Ehrerbietung vor allem Strengen und Härten hat.»

**出处**：PG eBook **#7204（德文）**，同上 URL；第九章「Was ist Vornehm?」内 §260（文本内编号 "260."）。本地快照行 6216–6262。

**对照判定**：**一致**。
- 命名句逐词对应：Herren-Moral / Sklaven-Moral = master-morality / slave-morality；
- 解毒剂句："not or fast nicht aus Mitleid, sondern mehr aus einem Drang, den der Überfluss von Macht erzeugt" = "not—or scarcely—out of pity, but rather from an impulse generated by the super-abundance of power"，逐词对应（Zimmern 的 "scarcely" 译 "fast nicht"、"impulse" 译 "Drang"，均准）；
- "mit Lust Strenge und Härte gegen sich übt" = "takes pleasure in subjecting himself to severity and hardness"，语义一致（"mit Lust"→"takes pleasure"）。
- 「『好』的自我设定」面：«Die vornehme Art Mensch fühlt sich als werthbestimmend … sie ist wertheschaffend» 支撑 03/09「法则性质/权威来源」行的转述，无冲突。

**置信说明**：高。德文逐字照抄自 PG 德文全本；两处英译主张（命名 + 解毒剂）均与原文吻合，09 对 §260 的两处使用（§2.2 高贵者自尊、§4.2 反冷漠解毒剂）文本地基扎实。

---

## 5. Za I:15——「人类把善与恶给予自己」

**英译主张**（09 §2.1，Common 译 PG #1998 XV "The Thousand and One Goals"）：
> "Verily, men have given unto themselves all their good and bad. Verily, they took it not, they found it not, it came not unto them as a voice from heaven."
> "A table of excellencies hangeth over every people… it is the voice of their Will to Power."
> "Valuing is creating… Through valuation only is there value."
> "Change of values—that is, change of the creating ones. Always doth he destroy who hath to be a creator."
> "Creating ones were first of all peoples, and only in late times individuals."

**德文原文照抄**（PG 德文纯文本逐字，旧正字法）：

> «Viele Länder sah Zarathustra und viele Völker: so entdeckte er vieler Völker Gutes und Böses. Keine grössere Macht fand Zarathustra auf Erden, als Gut und Böse. …
> **Eine Tafel der Güter hängt über jedem Volke. Siehe, es ist seiner Überwindungen Tafel; siehe, es ist die Stimme seines Willens zur Macht.** …
> **Wahrlich, die Menschen gaben sich alles ihr Gutes und Böses. Wahrlich, sie nahmen es nicht, sie fanden es nicht, nicht fiel es ihnen als Stimme vom Himmel.** …
> **Werthe legte erst der Mensch in die Dinge, sich zu erhalten,—er schuf erst den Dingen Sinn, einen Menschen-Sinn!** Darum nennt er sich "Mensch", das ist: der Schätzende.
> **Schätzen ist Schaffen: hört es, ihr Schaffenden! Schätzen selber ist aller geschätzten Dinge Schatz und Kleinod. Durch das Schätzen erst giebt es Werth: und ohne das Schätzen wäre die Nuss des Daseins hohl.** …
> **Wandel der Werthe,—das ist Wandel der Schaffenden. Immer vernichtet, wer ein Schöpfer sein muss.** …
> **Schaffende waren erst Völker und spät erst Einzelne; wahrlich, der Einzelne selber ist noch die jüngste Schöpfung.** …
> Liebende waren es stets und Schaffende, die schufen Gut und Böse. Feuer der Liebe glüht in aller Tugenden Namen und Feuer des Zorns. …
> Tausend Ziele gab es bisher, denn tausend Völker gab es. Nur die Fessel der tausend Nacken fehlt noch, es fehlt das Eine Ziel. Noch hat die Menschheit kein Ziel.»

**出处**：Friedrich Nietzsche, *Also sprach Zarathustra*, Project Gutenberg eBook **#7205（德文）**，https://www.gutenberg.org/cache/epub/7205/pg7205.txt ；第一部第 15 章「Von tausend und Einem Ziele」（= Common 译本 XV；= 分部计数 Z I:15）。本地快照行 2202–2287。

**对照判定**：**一致**。
- "men have given unto themselves all their good and bad" ↔ «die Menschen gaben sich alles ihr Gutes und Böses»；
- "they took it not, they found it not, it came not unto them as a voice from heaven" ↔ «sie nahmen es nicht, sie fanden es nicht, nicht fiel es ihnen als Stimme vom Himmel»（Common 的 "came not unto them as" 与德文 "nicht fiel es ihnen als … vom Himmel"〔不是作为天之音落在他们身上〕语义相当）；
- "A table of excellencies hangeth over every people" ↔ «Eine Tafel der Güter hängt über jedem Volke»；「it is the voice of their Will to Power」↔ «es ist die Stimme seines Willens zur Macht»；
- "Valuing is creating… Through valuation only is there value" ↔ «Schätzen ist Schaffen… Durch das Schätzen erst giebt es Werth»；
- "Change of values—that is, change of the creating ones. Always doth he destroy who hath to be a creator" ↔ «Wandel der Werthe,—das ist Wandel der Schaffenden. Immer vernichtet, wer ein Schöpfer sein muss»；
- "Creating ones were first of all peoples, and only in late times individuals" ↔ «Schaffende waren erst Völker und spät erst Einzelne»。
另：09 引的「爱与创造之火」段有原文支撑：«Liebende waren es stets und Schaffende, die schufen Gut und Böse. Feuer der Liebe glüht in aller Tugenden Namen und Feuer des Zorns.»

**措辞提示（非英译偏差）**：委托任务书给出的德文意写「der Mensch legte sich Güte und Böse selber bei / sich selber Güte und Schlechtigkeit gab」**并非原文措辞**——Za I:15 逐字原文为 «die Menschen gaben sich alles ihr Gutes und Böses»（主语为复数 die Menschen，宾语为 alles ihr Gutes und Böses）。两稿实际使用的英译（Common）与德文一致；但如综合稿曾在脚注中采用上述德文意写句，建议替换为照抄原文。

**置信说明**：高。德文逐字照抄；Common 英译与德文逐句对应；09 的「价值创造初属诸民族、个人是最晚造物」论证（§2.1 关键限定）有 «Schaffende waren erst Völker und spät erst Einzelne» 直接支撑，证据链闭合。

---

## 6. Za II:12——生命自白「我即那必须永远超越自身者」

**英译主张**（09 §2.2，Common 译 XXXIV "Self-Surpassing"）：
> "Wherever I found a living thing, there found I Will to Power; and even in the will of the servant found I the will to be master."
> "I am that WHICH MUST EVER SURPASS ITSELF."
> "not, however, Will to Life, but…Will to Power!"
> "commanding is more difficult than obeying."
> "Yea, even when it commandeth itself, then also must it atone for its commanding. Of its own law must it become the judge and avenger and victim."
> "good and evil which would be everlasting—it doth not exist! Of its own accord must it ever surpass itself anew."

**德文原文照抄**（PG 德文纯文本逐字）：

> «Aber damit ihr mein Wort versteht vom Guten und Bösen: dazu will ich euch noch mein Wort vom Leben sagen und von der Art alles Lebendigen.
> Dem Lebendigen gieng ich nach, ich gieng die grössten und die kleinsten Wege, dass ich seine Art erkenne. …
> Aber, wo ich nur Lebendiges fand, da hörte ich auch die Rede vom Gehorsame. Alles Lebendige ist ein Gehorchendes. …
> **Diess aber ist das Dritte, was ich hörte: dass Befehlen schwerer ist, als Gehorchen.** Und nicht nur, dass der Befehlende die Last aller Gehorchenden trägt, und dass leicht ihn diese Last zerdrückt:—
> Ein Versuch und Wagniss erschien mir in allem Befehlen; und stets, wenn es befiehlt, wagt das Lebendige sich selber dran.
> **Ja noch, wenn es sich selber befiehlt: auch da noch muss es sein Befehlen büssen. Seinem eignen Gesetze muss es Richter und Rächer und Opfer werden.** …
> **Wo ich Lebendiges fand, da fand ich Willen zur Macht; und noch im Willen des Dienenden fand ich den Willen, Herr zu sein.** …
> Und diess Geheimniss redete das Leben selber zu mir. **Siehe, sprach es, ich bin das, was sich immer selber überwinden muss.** …
> Lieber noch gehe ich unter, als dass ich diesem Einen absagte; und wahrlich, wo es Untergang giebt und Blätterfallen, siehe, da opfert sich Leben—um Macht! …
> **Nur, wo Leben ist, da ist auch Wille: aber nicht Wille zum Leben, sondern—so lehre ich's dich—Wille zur Macht!** …
> Also lehrte mich einst das Leben: und daraus löse ich euch, ihr Weisesten, noch das Räthsel eures Herzens.
> **Wahrlich, ich sage euch: Gutes und Böses, das unvergänglich wäre—das giebt es nicht! Aus sich selber muss es sich immer wieder überwinden.**»

**出处**：PG eBook **#7205（德文）**，同上 URL；第二部第 12 章「Von der Selbst-Überwindung」（= Common 译本 XXXIV "Self-Surpassing"；= SEP/09 分部计数 Z II:12）。本地快照行 4506–4660。

**对照判定**：**一致**。
- "Wherever I found a living thing, there found I Will to Power; and even in the will of the servant found I the will to be master" ↔ «Wo ich Lebendiges fand, da fand ich Willen zur Macht; und noch im Willen des Dienenden fand ich den Willen, Herr zu sein»；
- "I am that WHICH MUST EVER SURPASS ITSELF" ↔ «ich bin das, was sich immer selber überwinden muss»；
- "commanding is more difficult than obeying" ↔ «dass Befehlen schwerer ist, als Gehorchen»；
- "even when it commandeth itself, then also must it atone for its commanding. Of its own law must it become the judge and avenger and victim" ↔ «Ja noch, wenn es sich selber befiehlt: auch da noch muss es sein Befehlen büssen. Seinem eignen Gesetze muss es Richter und Rächer und Opfer werden»；
- "not, however, Will to Life, but—so teach I you—Will to Power" ↔ «aber nicht Wille zum Leben, sondern—so lehre ich's dich—Wille zur Macht»；
- "good and evil which would be everlasting—it doth not exist! Of its own accord must it ever surpass itself anew" ↔ «Gutes und Böses, das unvergänglich wäre—das giebt es nicht! Aus sich selber muss es sich immer wieder überwinden»。

**置信说明**：高。德文逐字照抄；09 §2.2 的四处使用（权力意志=自我超越、发令难于服从、自我命令内嵌赎偿、无恒常善恶）均逐句落在德文原文上，英译无走样；09 转引中 "atone for its commanding"（为自己的命令赎偿）与德文 «muss es sein Befehlen büssen» 完全对应。

---

## 7. GMS 4:432——自律公式德文原文

**英译主张**（03 §1.1(a)，Abbott 译 PG #5682，原标〔SEP 核〕）：
> "the idea of the will of every rational being as a will that legislates universal law"（自律公式＝定言命令第三表述，G 4:432）。

委托方提示的德文对应句：「Der Wille ist … als selbstgesetzgebend」。

**德文原文**：**未检得**。按铁律不凭记忆补写 KSA 文本。

**尝试记录（全部失败）**：
- `http://gutenberg.spiegel.de/philosophie/kant/2grund.htm`（任务书指定 spiegel 系）——curl 超时 2 次、FetchURL network error。
- `https://www.deutschestextarchiv.de/kant_grundlegung_1785`（DTA 1785 首版）——JS cookie 验证闸，curl 不可过；浏览器通道不可用。
- Project Gutenberg 站内检索 "grundlegung zur metaphysik"——无德文本（仅 Abbott 英译 #5682 等）。
- `https://de.wikisource.org/` GMS 各页——network error。
- `https://web.archive.org/` Wayback 存档 spiegel 页——network error。

**对照判定**：**未检得**。德文级核验未实现；03 现状（Abbott 英译逐句核 + SEP 页码交叉核）维持。

**置信说明**：失败模式同为通路层。提示：自律公式的德文通行句为「…der bloße Gedanke einer allgemeinen Gesetzgebung… / handle nur nach derjenigen Maxime, durch die du zugleich wollen kannst, daß sie ein allgemeines Gesetz werde」与 4:432 的「der Wille als selbstgesetzgebend / der Satz der Selbstgesetzgebung」相关段落——此系记忆层信息，**未经原文照抄，不作定案依据**；待 spiegel/KSA/DTA 通路恢复后照抄闭环。

---

## 8. 《何谓启蒙》8:35——「Habe Mut, dich deines eigenen Verstandes zu bedienen」

**主张**（03 §4.1 已做德文逐句核实；本轮独立复核并处理委托方点名的「ungestaltetes Vieh」疑误）：
> "Aufklärung ist der Ausgang des Menschen aus seiner selbstverschuldeten Unmündigkeit… Sapere aude! Habe Mut, dich deines eigenen Verstandes zu bedienen! ist also der Wahlspruch der Aufklärung."
> 委托方指正：此前某处如出现「ungestaltetes Vieh」系误记，正解应为「unmündig」段。

**德文原文照抄**（PG #30821 纯文本逐字；原文件以等号 `=…=` 标记 emphasis，此处照排并保留，附清洗注）：

> «=Aufklärung ist der Ausgang des Menschen aus seiner selbstverschuldeten Unmündigkeit.= =Unmündigkeit= ist das Unvermögen, sich seines Verstandes ohne Leitung eines anderen zu bedienen. =Selbstverschuldet= ist diese Unmündigkeit, wenn die Ursache derselben nicht am Mangel des Verstandes, sondern der Entschließung und des Mutes liegt, sich seiner ohne Leitung eines andern zu bedienen. _Sapere aude!_ **Habe Mut, dich deines =eigenen= Verstandes zu bedienen!** ist also der Wahlspruch der Aufklärung.»（本地快照行 56–64；`=…=` 为 PG 纯文本的着重标记）

附：同文「自我立法试金石」段（03 §4.2 德文主张，本轮一并复核）：

> «Der Probierstein alles dessen, was über ein Volk als Gesetz beschlossen werden kann, liegt in der Frage: **ob ein Volk sich selbst wohl ein solches Gesetz auferlegen könnte?**»（本地快照行 213–215）

**出处**：Immanuel Kant, *Beantwortung der Frage: Was ist Aufklärung?*, Project Gutenberg eBook **#30821（德文，据 Bruno Cassirer 1913 年《康德著作集》第四卷）**，https://www.gutenberg.org/cache/epub/30821/pg30821.txt ；开篇首段（Ak 8:35）+ 宗教契约段（8:39 一带，通行页码，未逐页核）。

**对照判定**：**一致**，且**完成委托方点名证伪**：
- 座右铭句逐字确认：«Sapere aude! Habe Mut, dich deines eigenen Verstandes zu bedienen! ist also der Wahlspruch der Aufklärung.»——与 03 §4.1 所引完全一致（03 当时已标「德文逐句核实」，本轮为独立复核，结论不变）；
- 「ungestaltetes Vieh」证伪：对全文（本地快照 40,667 字符）检索 «Vieh»——**0 命中**；检索 «unmündig» 系——多处命中。故《何谓启蒙》中德文词为 **«unmündig» / «Unmündigkeit»（不成熟状态）**，不存在「ungestaltetes Vieh」（未成形的牲畜）字样；如综合稿任何位置出现后者，判为误记，应改为 unmündig 段。
- 附段复核：«ob ein Volk sich selbst wohl ein solches Gesetz auferlegen könnte?» 与 03 §4.2 引文一致。

**置信说明**：高。PG #30821 德文全本照抄；两处德文主张（启蒙定义 + 立法试金石）逐字复核通过；「Vieh」证伪为全文穷尽检索（0 命中），证据强度高。

---

## 总判

- **一致 5 条**：#3（JGB §211）、#4（JGB §260）、#5（Za I:15）、#6（Za II:12）、#8（《何谓启蒙》8:35）。其中 #8 附带完成点名证伪（「Vieh」0 命中）；#5 附带措辞提示（委托方德文意写 ≠ 原文，两稿英译本身一致）。
- **偏差 0 条**：英译主张与德文原文之间未发现走样；03/09 的中译转述亦全部落在原文上。
- **未检得 3 条**：#1（GM I §10）、#2（GM I §2）、#7（GMS 4:432）。均为德文**源通路**失败（Cloudflare 403 / JS 验证闸 / 整站不可达），非文本不存在；03/09 原有的「英译已核、德文未核」标注维持，待通路恢复后补照抄。

## 局限声明

1. **未检得 3 条的失败模式**：本轮可用的直连网络仅 gutenberg.org 稳定；projekt-gutenberg.org 正文页间歇 403（同站前言页可过，正文页被闸）；gutenberg.spiegel.de、de.wikisource.org、archive.org、zeno.org 整站不可达；deutschestextarchiv.de 与 textlog.de 有 JS 验证/纯 JS 应用壳；桌面浏览器通道中途不可用（渲染器无响应）。以上均记为通路问题，不得反向解读为「引文无德文出处」。
2. **未检得条目的纪律**：#1/#2/#7 未给出任何德文照抄句；任务书/记忆中流传的德文对应句一律不作定案依据。闭环路径：projekt-gutenberg 正文页（Cloudflare 通过策略）或 KSA/DTA 通路恢复后，按本报告各节「英译主张」逐句补照抄即可。
3. **底本说明**：JGB/Za 德文底本为 Project Gutenberg #7204/#7205（公版德文全本，旧正字法，如 Werth/diess/giebt 系原文正字而非讹误）；《何谓启蒙》底本为 PG #30821（Cassirer 1913 传本）。PG 无 GM 德文本（已逐号探测 #7194–#7208 并站内检索），故 GM 德文只能走 Gutenberg-DE 系，待通路。
4. **PG 纯文本标记**：#30821 以 `=…=` 表着重、`_…_` 表斜体；本报告照排保留并加注，未做无标记清洗以避免二校引入误差。
5. **学院版页码**：本轮仅 #8 涉及页码标注（8:35 系 03 已标「通行」，本轮未逐页核科学院版）；其余条目均为章节级定位，未涉页码层。
6. **中译对照范围**：03/09 两稿的全部相关中译转述本轮均与德文原文做了落点比对（非抽样），覆盖 #3–#6、#8 的每一句引用；未发现一处误译。
