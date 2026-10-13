// The window follows Painter's language, which Painter passes as --language.
// English is the source text and its own key, so call sites read as the
// sentence they show and a missing translation falls back to English rather
// than to a key name.

export const languages = ["en", "zh", "ja", "ko", "de", "fr", "es", "it", "pt"] as const
export type Language = typeof languages[number]

export function resolveLanguage(code: string | undefined): Language {
  const root = (code ?? "").toLowerCase().split(/[-_]/)[0]
  return languages.find(candidate => candidate === root) ?? "en"
}

function argumentLanguage(argv: readonly string[]): string | undefined {
  const index = argv.indexOf("--language")
  return index >= 0 ? argv[index + 1] : undefined
}

// Read from the command line as this module loads, not in main(): the theme
// picks its font by language, and style constants capture it at import time.
let current: Language = resolveLanguage(argumentLanguage(process.argv))

export const language = (): Language => current

/** For tests; the app's language is fixed for the life of the process. */
export function setLanguage(next: Language): void {
  current = next
}

export function t(source: string, values: Record<string, string | number> = {}): string {
  const column = languages.indexOf(current) - 1
  const template = column < 0 ? source : translations[source]?.[column] ?? source
  return template.replace(/\{(\w+)\}/g, (placeholder, name: string) =>
    name in values ? String(values[name]) : placeholder)
}

type Row = readonly [zh: string, ja: string, ko: string, de: string, fr: string, es: string, it: string, pt: string]

export const translations: Record<string, Row> = {
  // Toolbar and panels
  "Texture Set:": ["纹理集：", "テクスチャセット：", "텍스처 세트:", "Textursatz:", "Jeu de textures :", "Conjunto de texturas:", "Set texture:", "Conjunto de texturas:"],
  "Channel:": ["通道：", "チャンネル：", "채널:", "Kanal:", "Canal :", "Canal:", "Canale:", "Canal:"],
  "Render:": ["渲染：", "レンダー：", "렌더:", "Rendern:", "Rendu :", "Render:", "Render:", "Render:"],
  "Reset mapping": ["重置映射", "マッピングをリセット", "매핑 재설정", "Zuordnung zurücksetzen", "Réinitialiser le mappage", "Restablecer asignación", "Reimposta mappatura", "Redefinir mapeamento"],
  "Undo": ["撤销", "取り消す", "실행 취소", "Rückgängig", "Annuler", "Deshacer", "Annulla", "Desfazer"],
  "Redo": ["重做", "やり直す", "다시 실행", "Wiederholen", "Rétablir", "Rehacer", "Ripeti", "Refazer"],
  "Apply": ["应用", "適用", "적용", "Anwenden", "Appliquer", "Aplicar", "Applica", "Aplicar"],
  "Reload the saved PSD": ["重新加载已保存的 PSD", "保存済みの PSD を再読み込み", "저장된 PSD 다시 불러오기", "Gespeicherte PSD neu laden", "Recharger le PSD enregistré", "Recargar el PSD guardado", "Ricarica il PSD salvato", "Recarregar o PSD salvo"],
  "Change Photoshop document": ["更换 Photoshop 文档", "Photoshop ドキュメントを変更", "Photoshop 문서 변경", "Photoshop-Dokument wechseln", "Changer de document Photoshop", "Cambiar documento de Photoshop", "Cambia documento Photoshop", "Trocar documento do Photoshop"],
  "Connect Photoshop": ["连接 Photoshop", "Photoshop に接続", "Photoshop 연결", "Photoshop verbinden", "Connecter Photoshop", "Conectar Photoshop", "Collega Photoshop", "Conectar Photoshop"],
  "Connecting...": ["正在连接...", "接続中...", "연결 중...", "Verbindung wird hergestellt...", "Connexion...", "Conectando...", "Connessione...", "Conectando..."],
  "No document connected": ["未连接文档", "ドキュメント未接続", "연결된 문서 없음", "Kein Dokument verbunden", "Aucun document connecté", "Ningún documento conectado", "Nessun documento collegato", "Nenhum documento conectado"],
  "No snapshot loaded": ["未加载快照", "スナップショット未読み込み", "불러온 스냅샷 없음", "Kein Snapshot geladen", "Aucun instantané chargé", "Ninguna instantánea cargada", "Nessuna istantanea caricata", "Nenhum instantâneo carregado"],

  // Mapping help
  "How mapping works": ["映射的用法", "マッピングの使い方", "매핑 사용법", "So funktioniert die Zuordnung", "Fonctionnement du mappage", "Cómo funciona la asignación", "Come funziona la mappatura", "Como o mapeamento funciona"],
  "Drag layers from one side to the other.": ["把图层从一侧拖到另一侧。", "レイヤーを片側からもう片側へドラッグします。", "레이어를 한쪽에서 다른 쪽으로 드래그합니다.", "Ziehen Sie Ebenen von einer Seite auf die andere.", "Faites glisser les calques d'un côté à l'autre.", "Arrastre las capas de un lado al otro.", "Trascina i livelli da un lato all'altro.", "Arraste as camadas de um lado para o outro."],
  "Aim at the top of a row to place them above it, or lower to place them below.": ["对准某一行的上部会放到它上方，靠下则放到它下方。", "行の上部を狙うとその上に、下寄りを狙うとその下に配置されます。", "행의 위쪽을 겨냥하면 그 위에, 아래쪽을 겨냥하면 그 아래에 놓입니다.", "Zielen Sie auf den oberen Teil einer Zeile, um darüber einzufügen, oder tiefer, um darunter einzufügen.", "Visez le haut d'une ligne pour les placer au-dessus, ou plus bas pour les placer en dessous.", "Apunte a la parte superior de una fila para colocarlas encima, o más abajo para colocarlas debajo.", "Punta alla parte alta di una riga per inserirli sopra, o più in basso per inserirli sotto.", "Mire a parte superior de uma linha para colocá-las acima, ou mais abaixo para colocá-las embaixo."],
  "Drop onto a folder to put them inside.": ["拖到文件夹上会放进文件夹。", "フォルダーにドロップすると中に入ります。", "폴더에 놓으면 폴더 안으로 들어갑니다.", "Legen Sie sie auf einem Ordner ab, um sie hineinzulegen.", "Déposez-les sur un dossier pour les y placer.", "Suéltelas sobre una carpeta para colocarlas dentro.", "Rilasciali su una cartella per inserirli al suo interno.", "Solte sobre uma pasta para colocá-las dentro."],
  "Nothing is copied until you press Apply.": ["按下“应用”之前不会复制任何内容。", "「適用」を押すまで何もコピーされません。", "적용을 누르기 전에는 아무것도 복사되지 않습니다.", "Es wird nichts kopiert, bis Sie auf Anwenden klicken.", "Rien n'est copié tant que vous n'appuyez pas sur Appliquer.", "No se copia nada hasta que pulse Aplicar.", "Non viene copiato nulla finché non premi Applica.", "Nada é copiado até você pressionar Aplicar."],

  // Status line
  "Drag layers between Photoshop and Painter to map a transfer": ["在 Photoshop 和 Painter 之间拖动图层来建立传输", "Photoshop と Painter の間でレイヤーをドラッグして転送をマッピングします", "Photoshop과 Painter 사이에서 레이어를 드래그하여 전송을 매핑합니다", "Ziehen Sie Ebenen zwischen Photoshop und Painter, um eine Übertragung zuzuordnen", "Faites glisser des calques entre Photoshop et Painter pour mapper un transfert", "Arrastre capas entre Photoshop y Painter para asignar una transferencia", "Trascina i livelli tra Photoshop e Painter per mappare un trasferimento", "Arraste camadas entre o Photoshop e o Painter para mapear uma transferência"],
  "Connect Photoshop to start mapping layers": ["连接 Photoshop 后即可开始映射图层", "Photoshop に接続するとレイヤーのマッピングを開始できます", "Photoshop을 연결하면 레이어 매핑을 시작할 수 있습니다", "Verbinden Sie Photoshop, um mit der Zuordnung von Ebenen zu beginnen", "Connectez Photoshop pour commencer à mapper des calques", "Conecte Photoshop para empezar a asignar capas", "Collega Photoshop per iniziare a mappare i livelli", "Conecte o Photoshop para começar a mapear camadas"],
  "{count} selected": ["已选择 {count} 个", "{count} 個を選択", "{count}개 선택됨", "{count} ausgewählt", "{count} sélectionné(s)", "{count} seleccionadas", "{count} selezionati", "{count} selecionadas"],
  "{count} pending transfer": ["{count} 个待应用的传输", "保留中の転送 {count} 件", "대기 중인 전송 {count}개", "{count} ausstehende Übertragung", "{count} transfert en attente", "{count} transferencia pendiente", "{count} trasferimento in sospeso", "{count} transferência pendente"],
  "{count} pending transfers": ["{count} 个待应用的传输", "保留中の転送 {count} 件", "대기 중인 전송 {count}개", "{count} ausstehende Übertragungen", "{count} transferts en attente", "{count} transferencias pendientes", "{count} trasferimenti in sospeso", "{count} transferências pendentes"],
  "{count} to delete": ["{count} 个待删除", "削除予定 {count} 件", "삭제 예정 {count}개", "{count} zu löschen", "{count} à supprimer", "{count} por eliminar", "{count} da eliminare", "{count} a excluir"],
  "This target has pending transfers": ["此目标有待应用的传输", "このターゲットには保留中の転送があります", "이 대상에 대기 중인 전송이 있습니다", "Dieses Ziel hat ausstehende Übertragungen", "Cette cible a des transferts en attente", "Este destino tiene transferencias pendientes", "Questa destinazione ha trasferimenti in sospeso", "Este destino tem transferências pendentes"],
  "Layer removed from this mapping session": ["已从本次映射中移除图层", "このマッピングからレイヤーを除外しました", "이 매핑에서 레이어를 제외했습니다", "Ebene aus dieser Zuordnung entfernt", "Calque retiré de ce mappage", "Capa quitada de esta asignación", "Livello rimosso da questa mappatura", "Camada removida deste mapeamento"],
  "Mapping updated": ["映射已更新", "マッピングを更新しました", "매핑이 업데이트되었습니다", "Zuordnung aktualisiert", "Mappage mis à jour", "Asignación actualizada", "Mappatura aggiornata", "Mapeamento atualizado"],
  "Last mapping undone": ["已撤销上一次映射", "直前のマッピングを取り消しました", "마지막 매핑을 실행 취소했습니다", "Letzte Zuordnung rückgängig gemacht", "Dernier mappage annulé", "Última asignación deshecha", "Ultima mappatura annullata", "Último mapeamento desfeito"],
  "Last mapping restored": ["已恢复上一次映射", "直前のマッピングをやり直しました", "마지막 매핑을 다시 실행했습니다", "Letzte Zuordnung wiederhergestellt", "Dernier mappage rétabli", "Última asignación rehecha", "Ultima mappatura ripristinata", "Último mapeamento refeito"],
  "Mapping reset": ["映射已重置", "マッピングをリセットしました", "매핑을 재설정했습니다", "Zuordnung zurückgesetzt", "Mappage réinitialisé", "Asignación restablecida", "Mappatura reimpostata", "Mapeamento redefinido"],
  "Apply or reset pending transfers before changing the target.": ["更改目标前，请先应用或重置待应用的传输。", "ターゲットを変更する前に、保留中の転送を適用またはリセットしてください。", "대상을 변경하기 전에 대기 중인 전송을 적용하거나 재설정하십시오.", "Wenden Sie ausstehende Übertragungen an oder setzen Sie sie zurück, bevor Sie das Ziel wechseln.", "Appliquez ou réinitialisez les transferts en attente avant de changer de cible.", "Aplique o restablezca las transferencias pendientes antes de cambiar el destino.", "Applica o reimposta i trasferimenti in sospeso prima di cambiare destinazione.", "Aplique ou redefina as transferências pendentes antes de trocar o destino."],
  "Apply or reset pending transfers before changing documents.": ["更改文档前，请先应用或重置待应用的传输。", "ドキュメントを変更する前に、保留中の転送を適用またはリセットしてください。", "문서를 변경하기 전에 대기 중인 전송을 적용하거나 재설정하십시오.", "Wenden Sie ausstehende Übertragungen an oder setzen Sie sie zurück, bevor Sie das Dokument wechseln.", "Appliquez ou réinitialisez les transferts en attente avant de changer de document.", "Aplique o restablezca las transferencias pendientes antes de cambiar de documento.", "Applica o reimposta i trasferimenti in sospeso prima di cambiare documento.", "Aplique ou redefina as transferências pendentes antes de trocar de documento."],
  "Pending transfers kept · apply or reset them to reload the layers": ["已保留待应用的传输 · 应用或重置后才能重新加载图层", "保留中の転送を維持しました · レイヤーを再読み込みするには適用またはリセットしてください", "대기 중인 전송을 유지했습니다 · 레이어를 다시 불러오려면 적용하거나 재설정하십시오", "Ausstehende Übertragungen beibehalten · zum Neuladen der Ebenen anwenden oder zurücksetzen", "Transferts en attente conservés · appliquez-les ou réinitialisez-les pour recharger les calques", "Transferencias pendientes conservadas · aplíquelas o restablézcalas para recargar las capas", "Trasferimenti in sospeso mantenuti · applicali o reimpostali per ricaricare i livelli", "Transferências pendentes mantidas · aplique ou redefina para recarregar as camadas"],
  "Reading this target's Photoshop document...": ["正在读取此目标的 Photoshop 文档...", "このターゲットの Photoshop ドキュメントを読み込み中...", "이 대상의 Photoshop 문서를 읽는 중...", "Photoshop-Dokument dieses Ziels wird gelesen...", "Lecture du document Photoshop de cette cible...", "Leyendo el documento de Photoshop de este destino...", "Lettura del documento Photoshop di questa destinazione...", "Lendo o documento do Photoshop deste destino..."],
  "Target changed · {target}": ["目标已更改 · {target}", "ターゲットを変更しました · {target}", "대상이 변경되었습니다 · {target}", "Ziel gewechselt · {target}", "Cible modifiée · {target}", "Destino cambiado · {target}", "Destinazione cambiata · {target}", "Destino alterado · {target}"],
  "Choose a Photoshop document in Painter...": ["请在 Painter 中选择 Photoshop 文档...", "Painter で Photoshop ドキュメントを選択してください...", "Painter에서 Photoshop 문서를 선택하십시오...", "Wählen Sie in Painter ein Photoshop-Dokument...", "Choisissez un document Photoshop dans Painter...", "Elija un documento de Photoshop en Painter...", "Scegli un documento Photoshop in Painter...", "Escolha um documento do Photoshop no Painter..."],
  "Photoshop connection cancelled": ["已取消连接 Photoshop", "Photoshop への接続をキャンセルしました", "Photoshop 연결이 취소되었습니다", "Photoshop-Verbindung abgebrochen", "Connexion à Photoshop annulée", "Conexión con Photoshop cancelada", "Collegamento a Photoshop annullato", "Conexão com o Photoshop cancelada"],
  "Photoshop connection failed": ["连接 Photoshop 失败", "Photoshop への接続に失敗しました", "Photoshop 연결에 실패했습니다", "Photoshop-Verbindung fehlgeschlagen", "Échec de la connexion à Photoshop", "Error al conectar con Photoshop", "Collegamento a Photoshop non riuscito", "Falha na conexão com o Photoshop"],
  "Reading the saved PSD...": ["正在读取已保存的 PSD...", "保存済みの PSD を読み込み中...", "저장된 PSD를 읽는 중...", "Gespeicherte PSD wird gelesen...", "Lecture du PSD enregistré...", "Leyendo el PSD guardado...", "Lettura del PSD salvato...", "Lendo o PSD salvo..."],
  "Reloading layers...": ["正在重新加载图层...", "レイヤーを再読み込み中...", "레이어를 다시 불러오는 중...", "Ebenen werden neu geladen...", "Rechargement des calques...", "Recargando capas...", "Ricaricamento dei livelli...", "Recarregando camadas..."],
  "Layers reloaded": ["图层已重新加载", "レイヤーを再読み込みしました", "레이어를 다시 불러왔습니다", "Ebenen neu geladen", "Calques rechargés", "Capas recargadas", "Livelli ricaricati", "Camadas recarregadas"],
  "The old layer will be deleted on Apply": ["应用时将删除旧图层", "適用時に古いレイヤーを削除します", "적용 시 이전 레이어가 삭제됩니다", "Die alte Ebene wird beim Anwenden gelöscht", "L'ancien calque sera supprimé à l'application", "La capa antigua se eliminará al aplicar", "Il vecchio livello verrà eliminato all'applicazione", "A camada antiga será excluída ao aplicar"],
  "The old layer is kept": ["保留旧图层", "古いレイヤーを残します", "이전 레이어를 유지합니다", "Die alte Ebene bleibt erhalten", "L'ancien calque est conservé", "La capa antigua se conserva", "Il vecchio livello viene mantenuto", "A camada antiga é mantida"],

  // Rows
  "Pending": ["待应用", "保留中", "대기 중", "Ausstehend", "En attente", "Pendiente", "In sospeso", "Pendente"],
  "Replace": ["替换", "置き換え", "교체", "Ersetzen", "Remplacer", "Reemplazar", "Sostituisci", "Substituir"],
  "{note} · replaces {name}": ["{note} · 替换 {name}", "{note} · {name} を置き換え", "{note} · {name} 교체", "{note} · ersetzt {name}", "{note} · remplace {name}", "{note} · reemplaza {name}", "{note} · sostituisce {name}", "{note} · substitui {name}"],
  "Deleted on Apply · replaced by {names}": ["应用时删除 · 由 {names} 替换", "適用時に削除 · {names} に置き換え", "적용 시 삭제 · {names}(으)로 교체", "Wird beim Anwenden gelöscht · ersetzt durch {names}", "Supprimé à l'application · remplacé par {names}", "Se elimina al aplicar · reemplazada por {names}", "Eliminato all'applicazione · sostituito da {names}", "Excluída ao aplicar · substituída por {names}"],
  "{mode} becomes Normal": ["{mode} 将变为“正常”", "{mode} は通常になります", "{mode}은(는) 표준이 됩니다", "{mode} wird zu Normal", "{mode} devient Normal", "{mode} pasa a Normal", "{mode} diventa Normale", "{mode} passa a Normal"],
  "{count} layer skipped": ["跳过 {count} 个图层", "{count} レイヤーをスキップ", "레이어 {count}개 건너뜀", "{count} Ebene übersprungen", "{count} calque ignoré", "{count} capa omitida", "{count} livello ignorato", "{count} camada ignorada"],
  "{count} layers skipped": ["跳过 {count} 个图层", "{count} レイヤーをスキップ", "레이어 {count}개 건너뜀", "{count} Ebenen übersprungen", "{count} calques ignorés", "{count} capas omitidas", "{count} livelli ignorati", "{count} camadas ignoradas"],
  "Layer {index}": ["图层 {index}", "レイヤー {index}", "레이어 {index}", "Ebene {index}", "Calque {index}", "Capa {index}", "Livello {index}", "Camada {index}"],
  "Group": ["组", "グループ", "그룹", "Gruppe", "Groupe", "Grupo", "Gruppo", "Grupo"],
  "{count} Layers": ["{count} 个图层", "{count} レイヤー", "레이어 {count}개", "{count} Ebenen", "{count} calques", "{count} capas", "{count} livelli", "{count} camadas"],
  "Clipped to a folder · not supported": ["剪贴到文件夹 · 不支持", "フォルダーにクリップ · 非対応", "폴더에 클리핑됨 · 지원되지 않음", "An Ordner beschnitten · nicht unterstützt", "Écrêté sur un dossier · non pris en charge", "Recortada a una carpeta · no compatible", "Ritagliato su una cartella · non supportato", "Recortada em uma pasta · não compatível"],
  "Clipped · merges into {name}": ["剪贴图层 · 合并到 {name}", "クリップ · {name} に統合", "클리핑됨 · {name}에 병합", "Beschnitten · wird mit {name} zusammengeführt", "Écrêté · fusionne dans {name}", "Recortada · se combina con {name}", "Ritagliato · si unisce a {name}", "Recortada · mescla com {name}"],
  "Adjustment layer · not supported": ["调整图层 · 不支持", "調整レイヤー · 非対応", "조정 레이어 · 지원되지 않음", "Einstellungsebene · nicht unterstützt", "Calque de réglage · non pris en charge", "Capa de ajuste · no compatible", "Livello di regolazione · non supportato", "Camada de ajuste · não compatível"],
  "Fill colour model not supported": ["不支持该填充的颜色模式", "塗りつぶしのカラーモデルは非対応です", "칠 색상 모델이 지원되지 않습니다", "Farbmodell der Füllung nicht unterstützt", "Modèle de couleur du remplissage non pris en charge", "Modelo de color del relleno no compatible", "Modello colore del riempimento non supportato", "Modelo de cor do preenchimento não compatível"],
  "Shape layer · not supported": ["形状图层 · 不支持", "シェイプレイヤー · 非対応", "모양 레이어 · 지원되지 않음", "Formebene · nicht unterstützt", "Calque de forme · non pris en charge", "Capa de forma · no compatible", "Livello forma · non supportato", "Camada de forma · não compatível"],
  "Gradient or pattern fill · not supported": ["渐变或图案填充 · 不支持", "グラデーションまたはパターン塗り · 非対応", "그레이디언트 또는 패턴 칠 · 지원되지 않음", "Verlaufs- oder Musterfüllung · nicht unterstützt", "Remplissage en dégradé ou motif · non pris en charge", "Relleno de degradado o motivo · no compatible", "Riempimento sfumatura o pattern · non supportato", "Preenchimento de degradê ou padrão · não compatível"],
  "Empty layer": ["空图层", "空のレイヤー", "빈 레이어", "Leere Ebene", "Calque vide", "Capa vacía", "Livello vuoto", "Camada vazia"],
  "colour fill": ["纯色填充", "べた塗り", "단색 칠", "Farbfüllung", "remplissage uni", "relleno de color", "riempimento colore", "preenchimento de cor"],
  "Colour fill": ["纯色填充", "べた塗り", "단색 칠", "Farbfüllung", "Remplissage uni", "Relleno de color", "Riempimento colore", "Preenchimento de cor"],
  "merges {count} clipped": ["合并 {count} 个剪贴图层", "クリップ {count} 件を統合", "클리핑 {count}개 병합", "führt {count} beschnittene zusammen", "fusionne {count} écrêté(s)", "combina {count} recortadas", "unisce {count} ritagliati", "mescla {count} recortadas"],
  "Merges {count} clipped": ["合并 {count} 个剪贴图层", "クリップ {count} 件を統合", "클리핑 {count}개 병합", "Führt {count} beschnittene zusammen", "Fusionne {count} écrêté(s)", "Combina {count} recortadas", "Unisce {count} ritagliati", "Mescla {count} recortadas"],
  "styles not transferred": ["图层样式不会传输", "スタイルは転送されません", "스타일은 전송되지 않음", "Stile werden nicht übertragen", "styles non transférés", "estilos no transferidos", "stili non trasferiti", "estilos não transferidos"],
  "Styles not transferred": ["图层样式不会传输", "スタイルは転送されません", "스타일은 전송되지 않음", "Stile werden nicht übertragen", "Styles non transférés", "Estilos no transferidos", "Stili non trasferiti", "Estilos não transferidos"],
  "{name}: {reason}, skipped.": ["{name}：{reason}，已跳过。", "{name}：{reason}、スキップしました。", "{name}: {reason}, 건너뜀.", "{name}: {reason}, übersprungen.", "{name} : {reason}, ignoré.", "{name}: {reason}, omitida.", "{name}: {reason}, ignorato.", "{name}: {reason}, ignorada."],

  // Apply
  "Preparing mapped items...": ["正在准备已映射的项目...", "マッピングした項目を準備中...", "매핑된 항목 준비 중...", "Zugeordnete Elemente werden vorbereitet...", "Préparation des éléments mappés...", "Preparando los elementos asignados...", "Preparazione degli elementi mappati...", "Preparando os itens mapeados..."],
  "Applying in Painter...": ["正在 Painter 中应用...", "Painter で適用中...", "Painter에서 적용 중...", "Wird in Painter angewendet...", "Application dans Painter...", "Aplicando en Painter...", "Applicazione in Painter...", "Aplicando no Painter..."],
  "Waiting for Painter...": ["正在等待 Painter...", "Painter を待機中...", "Painter 대기 중...", "Warten auf Painter...", "En attente de Painter...", "Esperando a Painter...", "In attesa di Painter...", "Aguardando o Painter..."],
  "Refreshing layer lists...": ["正在刷新图层列表...", "レイヤーリストを更新中...", "레이어 목록 새로 고치는 중...", "Ebenenlisten werden aktualisiert...", "Actualisation des listes de calques...", "Actualizando las listas de capas...", "Aggiornamento degli elenchi dei livelli...", "Atualizando as listas de camadas..."],
  "Applying changes": ["正在应用更改", "変更を適用中", "변경 사항 적용 중", "Änderungen werden angewendet", "Application des modifications", "Aplicando cambios", "Applicazione delle modifiche", "Aplicando alterações"],
  "Applying changes...": ["正在应用更改...", "変更を適用中...", "변경 사항 적용 중...", "Änderungen werden angewendet...", "Application des modifications...", "Aplicando cambios...", "Applicazione delle modifiche...", "Aplicando alterações..."],
  "Reading Photoshop layers": ["读取 Photoshop 图层", "Photoshop レイヤーを読み込み", "Photoshop 레이어 읽기", "Photoshop-Ebenen lesen", "Lecture des calques Photoshop", "Lectura de capas de Photoshop", "Lettura dei livelli Photoshop", "Leitura das camadas do Photoshop"],
  "Rendering Painter layers": ["渲染 Painter 图层", "Painter レイヤーをレンダリング", "Painter 레이어 렌더링", "Painter-Ebenen rendern", "Rendu des calques Painter", "Render de capas de Painter", "Rendering dei livelli Painter", "Renderização das camadas do Painter"],
  "Matching Painter's look": ["匹配 Painter 的外观", "Painter の見た目に合わせる", "Painter의 모양에 맞추기", "An das Aussehen in Painter anpassen", "Correspondance avec l'aspect de Painter", "Igualar el aspecto de Painter", "Corrispondenza con l'aspetto di Painter", "Igualar a aparência do Painter"],
  "Importing into Painter": ["导入 Painter", "Painter に読み込み", "Painter로 가져오기", "In Painter importieren", "Importation dans Painter", "Importación en Painter", "Importazione in Painter", "Importação no Painter"],
  "Inserting into Photoshop": ["插入 Photoshop", "Photoshop に挿入", "Photoshop에 삽입", "In Photoshop einfügen", "Insertion dans Photoshop", "Inserción en Photoshop", "Inserimento in Photoshop", "Inserção no Photoshop"],
  "Step {step} of {total}": ["第 {step} 步，共 {total} 步", "ステップ {step} / {total}", "{total}단계 중 {step}단계", "Schritt {step} von {total}", "Étape {step} sur {total}", "Paso {step} de {total}", "Passaggio {step} di {total}", "Etapa {step} de {total}"],
  "Layer “{name}”": ["图层“{name}”", "レイヤー「{name}」", "레이어 “{name}”", "Ebene „{name}“", "Calque « {name} »", "Capa «{name}»", "Livello “{name}”", "Camada “{name}”"],
  "Cancel": ["取消", "キャンセル", "취소", "Abbrechen", "Annuler", "Cancelar", "Annulla", "Cancelar"],
  "Cancelling...": ["正在取消...", "キャンセル中...", "취소 중...", "Wird abgebrochen...", "Annulation...", "Cancelando...", "Annullamento...", "Cancelando..."],
  "Writing into Painter and Photoshop; stopping now would leave them half-applied": ["正在写入 Painter 和 Photoshop；现在停止会只应用一半", "Painter と Photoshop に書き込み中です。今停止すると適用が途中のままになります", "Painter와 Photoshop에 쓰는 중입니다. 지금 중지하면 절반만 적용됩니다", "Es wird in Painter und Photoshop geschrieben; ein Abbruch jetzt würde sie halb angewendet zurücklassen", "Écriture dans Painter et Photoshop ; arrêter maintenant les laisserait à moitié appliqués", "Escribiendo en Painter y Photoshop; detenerlo ahora los dejaría a medio aplicar", "Scrittura in Painter e Photoshop; fermarsi ora li lascerebbe applicati a metà", "Gravando no Painter e no Photoshop; parar agora deixaria tudo aplicado pela metade"],
  "Apply cancelled. Nothing was changed in Painter or Photoshop.": ["已取消应用。Painter 和 Photoshop 均未更改。", "適用をキャンセルしました。Painter と Photoshop は変更されていません。", "적용이 취소되었습니다. Painter와 Photoshop은 변경되지 않았습니다.", "Anwenden abgebrochen. In Painter und Photoshop wurde nichts geändert.", "Application annulée. Rien n'a été modifié dans Painter ni dans Photoshop.", "Aplicación cancelada. No se ha cambiado nada en Painter ni en Photoshop.", "Applicazione annullata. Nulla è stato modificato in Painter o Photoshop.", "Aplicação cancelada. Nada foi alterado no Painter nem no Photoshop."],
  "Applied": ["已应用", "適用しました", "적용됨", "Angewendet", "Appliqué", "Aplicado", "Applicato", "Aplicado"],
  "Apply cancelled": ["已取消应用", "適用をキャンセルしました", "적용이 취소되었습니다", "Anwenden abgebrochen", "Application annulée", "Aplicación cancelada", "Applicazione annullata", "Aplicação cancelada"],
  "Apply failed": ["应用失败", "適用に失敗しました", "적용 실패", "Anwenden fehlgeschlagen", "Échec de l'application", "Error al aplicar", "Applicazione non riuscita", "Falha ao aplicar"],
  "Map at least one layer before Apply": ["应用前请至少映射一个图层", "適用する前に少なくとも 1 つのレイヤーをマッピングしてください", "적용하기 전에 레이어를 하나 이상 매핑하십시오", "Ordnen Sie vor dem Anwenden mindestens eine Ebene zu", "Mappez au moins un calque avant d'appliquer", "Asigne al menos una capa antes de aplicar", "Mappa almeno un livello prima di applicare", "Mapeie ao menos uma camada antes de aplicar"],
  "Painter closed the Bridge connection": ["Painter 已关闭 Bridge 连接", "Painter が Bridge の接続を閉じました", "Painter가 Bridge 연결을 닫았습니다", "Painter hat die Bridge-Verbindung geschlossen", "Painter a fermé la connexion Bridge", "Painter cerró la conexión de Bridge", "Painter ha chiuso la connessione Bridge", "O Painter fechou a conexão do Bridge"],
  "Only RGB Photoshop documents can be connected": ["只能连接 RGB 模式的 Photoshop 文档", "接続できるのは RGB の Photoshop ドキュメントのみです", "RGB Photoshop 문서만 연결할 수 있습니다", "Nur RGB-Photoshop-Dokumente können verbunden werden", "Seuls les documents Photoshop RVB peuvent être connectés", "Solo se pueden conectar documentos de Photoshop RGB", "È possibile collegare solo documenti Photoshop RGB", "Somente documentos RGB do Photoshop podem ser conectados"],
  "Photoshop layer is no longer in {name}": ["Photoshop 图层已不在 {name} 中", "Photoshop レイヤーは {name} にもうありません", "Photoshop 레이어가 더 이상 {name}에 없습니다", "Die Photoshop-Ebene ist nicht mehr in {name}", "Le calque Photoshop n'est plus dans {name}", "La capa de Photoshop ya no está en {name}", "Il livello Photoshop non è più in {name}", "A camada do Photoshop não está mais em {name}"],
  "A mapped Photoshop layer is no longer available": ["已映射的 Photoshop 图层已不可用", "マッピングした Photoshop レイヤーは利用できなくなりました", "매핑된 Photoshop 레이어를 더 이상 사용할 수 없습니다", "Eine zugeordnete Photoshop-Ebene ist nicht mehr verfügbar", "Un calque Photoshop mappé n'est plus disponible", "Una capa de Photoshop asignada ya no está disponible", "Un livello Photoshop mappato non è più disponibile", "Uma camada mapeada do Photoshop não está mais disponível"],
  "The selected Painter context is no longer available": ["所选的 Painter 目标已不可用", "選択した Painter のターゲットは利用できなくなりました", "선택한 Painter 대상을 더 이상 사용할 수 없습니다", "Das gewählte Painter-Ziel ist nicht mehr verfügbar", "La cible Painter sélectionnée n'est plus disponible", "El destino de Painter seleccionado ya no está disponible", "La destinazione Painter selezionata non è più disponibile", "O destino do Painter selecionado não está mais disponível"],

  // Replace confirmation
  "Delete {count} layer?": ["删除 {count} 个图层？", "{count} レイヤーを削除しますか？", "레이어 {count}개를 삭제하시겠습니까?", "{count} Ebene löschen?", "Supprimer {count} calque ?", "¿Eliminar {count} capa?", "Eliminare {count} livello?", "Excluir {count} camada?"],
  "Delete {count} layers?": ["删除 {count} 个图层？", "{count} レイヤーを削除しますか？", "레이어 {count}개를 삭제하시겠습니까?", "{count} Ebenen löschen?", "Supprimer {count} calques ?", "¿Eliminar {count} capas?", "Eliminare {count} livelli?", "Excluir {count} camadas?"],
  "Replaced by {names}": ["由 {names} 替换", "{names} に置き換え", "{names}(으)로 교체", "Ersetzt durch {names}", "Remplacé par {names}", "Reemplazada por {names}", "Sostituito da {names}", "Substituída por {names}"],
  "Each is deleted once its replacement is in place. Undo in that app brings it back.": ["替换的图层就位后才会删除旧图层。在对应的软件中撤销即可恢复。", "置き換えるレイヤーが配置されてから削除されます。そのアプリで取り消すと元に戻せます。", "교체 레이어가 배치된 후에 삭제됩니다. 해당 앱에서 실행 취소하면 복원됩니다.", "Jede wird gelöscht, sobald ihr Ersatz eingefügt ist. Rückgängig in der jeweiligen App stellt sie wieder her.", "Chacun est supprimé une fois son remplaçant en place. Annuler dans cette application le restaure.", "Cada una se elimina cuando su reemplazo está en su sitio. Deshacer en esa aplicación la recupera.", "Ognuno viene eliminato quando il sostituto è al suo posto. Annulla in quell'app lo ripristina.", "Cada uma é excluída quando a substituta está no lugar. Desfazer naquele aplicativo a traz de volta."],
  "Delete and apply": ["删除并应用", "削除して適用", "삭제 후 적용", "Löschen und anwenden", "Supprimer et appliquer", "Eliminar y aplicar", "Elimina e applica", "Excluir e aplicar"],
}
