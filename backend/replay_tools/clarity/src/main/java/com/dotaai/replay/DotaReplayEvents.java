package com.dotaai.replay;

import skadistats.clarity.event.Insert;
import skadistats.clarity.io.Util;
import skadistats.clarity.model.CombatLogEntry;
import skadistats.clarity.model.DTClass;
import skadistats.clarity.model.Entity;
import skadistats.clarity.model.FieldPath;
import skadistats.clarity.processor.entities.Entities;
import skadistats.clarity.processor.entities.OnEntityUpdated;
import skadistats.clarity.processor.entities.UsesEntities;
import skadistats.clarity.processor.gameevents.OnCombatLogEntry;
import skadistats.clarity.processor.reader.OnTickEnd;
import skadistats.clarity.processor.runner.Context;
import skadistats.clarity.processor.runner.SimpleRunner;
import skadistats.clarity.processor.sendtables.DTClasses;
import skadistats.clarity.processor.sendtables.OnDTClassesComplete;
import skadistats.clarity.source.MappedFileSource;
import skadistats.clarity.wire.dota.common.proto.DOTACombatLog;

import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Iterator;
import java.util.LinkedHashSet;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

import static java.lang.String.format;

@UsesEntities
public class DotaReplayEvents {

    private Options options;
    private BufferedWriter writer;
    private int eventCount;
    private int snapshotCount;

    @Insert
    private DTClasses dtClasses;

    @Insert
    private Entities entities;

    private DTClass playerResourceClass;
    private FieldPath selectedHeroFieldPath;
    private FieldPath gameTimePath;
    private Entity selectedHeroEntity;
    private String selectedHeroClassName = "";
    private int lastSnapshotSecond = -1;
    private boolean multipleMatchingHeroEntities;
    private boolean printedEntityDebug;
    private final Set<String> discoveredSnapshotFields = new LinkedHashSet<>();

    public static void main(String[] args) throws Exception {
        new DotaReplayEvents().run(args);
    }

    private void run(String[] args) throws Exception {
        options = Options.parse(args);
        if (options.help) {
            Options.printUsage();
            return;
        }

        Path parent = options.output.getParent();
        if (parent != null) {
            Files.createDirectories(parent);
        }

        try (
            BufferedWriter output = Files.newBufferedWriter(options.output, StandardCharsets.UTF_8);
            MappedFileSource source = new MappedFileSource(options.demo.toString())
        ) {
            writer = output;
            new SimpleRunner(source).runWith(this);
        }

        if (eventCount == 0) {
            throw new IllegalStateException(
                "No selected-player replay events were extracted. " +
                "Check --hero/--player-slot, time window, or use a richer parser. No fake events were written."
            );
        }

        System.err.printf("Replay events extracted: %d%n", eventCount);
        System.err.printf("Combat-log events extracted: %d%n", eventCount - snapshotCount);
        System.err.printf("Entity snapshots extracted: %d%n", snapshotCount);
        System.err.printf("Selected hero entity found: %s%n", selectedHeroEntity != null);
        if (notBlank(selectedHeroClassName)) {
            System.err.printf("Selected hero entity class: %s%n", selectedHeroClassName);
        }
        if (multipleMatchingHeroEntities) {
            System.err.println("Multiple matching hero entities were seen; player_slot PlayerResource handle was preferred.");
        }
        System.err.printf("Snapshot fields extracted: %s%n", discoveredSnapshotFields);
        System.err.printf("Output: %s%n", options.output);
    }

    @OnDTClassesComplete
    protected void onDtClassesComplete() {
        playerResourceClass = dtClasses.forDtName("CDOTA_PlayerResource");
        if (playerResourceClass == null) {
            return;
        }
        int resourceIndex = playerResourceIndex(options.playerSlot);
        if (resourceIndex < 0 || resourceIndex > 9) {
            return;
        }
        selectedHeroFieldPath = playerResourceClass.getFieldPathForName(
            format("m_vecPlayerTeamData.%s.m_hSelectedHero", Util.arrayIdxToString(resourceIndex))
        );
    }

    @OnEntityUpdated
    protected void onEntityUpdated(Entity entity, FieldPath[] changedFieldPaths, int nChangedFieldPaths) {
        if (entity.getDtClass() != playerResourceClass || selectedHeroFieldPath == null) {
            return;
        }
        for (int i = 0; i < nChangedFieldPaths; i++) {
            if (selectedHeroFieldPath.equals(changedFieldPaths[i])) {
                resolveSelectedHeroFromPlayerResource(entity);
                return;
            }
        }
    }

    @OnTickEnd
    protected void onTickEnd(Context context, boolean synthetic) throws IOException {
        ensureSelectedHeroEntity();
        if (selectedHeroEntity == null) {
            return;
        }

        int timestamp = currentReplaySecond(context);
        if (timestamp < options.startSeconds || timestamp > options.endSeconds) {
            return;
        }
        if (timestamp < 0 || timestamp == lastSnapshotSecond) {
            return;
        }
        if (lastSnapshotSecond >= 0 && timestamp - lastSnapshotSecond < options.snapshotIntervalSeconds) {
            return;
        }

        writeSnapshot(timestamp);
        lastSnapshotSecond = timestamp;
    }

    @OnCombatLogEntry
    public void onCombatLogEntry(CombatLogEntry cle) {
        int timestamp = (int) Math.floor(cle.getTimestamp());
        if (timestamp < options.startSeconds || timestamp > options.endSeconds) {
            return;
        }

        try {
            DOTACombatLog.DOTA_COMBATLOG_TYPES type = cle.getType();
            switch (type) {
                case DOTA_COMBATLOG_DEATH:
                    if (isSelectedTarget(cle)) {
                        writeDeath(cle, timestamp);
                    }
                    break;
                case DOTA_COMBATLOG_DAMAGE:
                    if (isSelectedTarget(cle)) {
                        writeDamage(cle, timestamp);
                    }
                    break;
                case DOTA_COMBATLOG_HEAL:
                case DOTA_COMBATLOG_MANA_RESTORED:
                    if (isSelectedTarget(cle)) {
                        writeHeal(cle, timestamp);
                    }
                    break;
                case DOTA_COMBATLOG_PURCHASE:
                    if (isSelectedTarget(cle)) {
                        writePurchase(cle, timestamp);
                    }
                    break;
                case DOTA_COMBATLOG_ABILITY:
                case DOTA_COMBATLOG_ABILITY_TRIGGER:
                case DOTA_COMBATLOG_ITEM:
                    if (isSelectedActor(cle)) {
                        writeAbility(cle, timestamp);
                    }
                    break;
                case DOTA_COMBATLOG_PLAYERSTATS:
                    if (isSelectedTarget(cle)) {
                        writePlayerStats(cle, timestamp);
                    }
                    break;
                case DOTA_COMBATLOG_HERO_LEVELUP:
                    if (isSelectedTarget(cle)) {
                        writeLevel(cle, timestamp);
                    }
                    break;
                case DOTA_COMBATLOG_LOCATION:
                    if (isSelectedTarget(cle)) {
                        writePosition(cle, timestamp);
                    }
                    break;
                case DOTA_COMBATLOG_TEAM_BUILDING_KILL:
                    writeObjective(cle, timestamp);
                    break;
                default:
                    break;
            }
        } catch (IOException exc) {
            throw new RuntimeException("Failed to write replay event JSONL", exc);
        }
    }

    private void writeDeath(CombatLogEntry cle, int timestamp) throws IOException {
        Map<String, Object> event = baseEvent(timestamp, "death");
        event.put("death", true);
        event.put("game_state", "dead");
        event.put("killer", cleanName(cle.getAttackerName()));
        event.put("event_context", "parsed from Dota replay combat log death event");
        event.put("context_confidence", "high");
        writeEvent(event);
    }

    private void writeDamage(CombatLogEntry cle, int timestamp) throws IOException {
        Map<String, Object> event = baseEvent(timestamp, "damage");
        if (cle.getValue() > 0) {
            event.put("damage", cle.getValue());
        }
        if (cle.getHealth() > 0) {
            event.put("health_after", cle.getHealth());
        }
        event.put("attacker", cleanName(cle.getAttackerName()));
        if (notBlank(cle.getInflictorName())) {
            event.put("ability", cleanName(cle.getInflictorName()));
        }
        event.put(
            "event_context",
            "parsed from Dota replay combat log damage event; exact HP percent unavailable"
        );
        event.put("context_confidence", "medium");
        writeEvent(event);
    }

    private void writeHeal(CombatLogEntry cle, int timestamp) throws IOException {
        Map<String, Object> event = baseEvent(timestamp, "heal");
        if (cle.getValue() > 0) {
            event.put("heal", cle.getValue());
        }
        if (cle.getHealth() > 0) {
            event.put("health_after", cle.getHealth());
        }
        if (notBlank(cle.getInflictorName())) {
            event.put("ability", cleanName(cle.getInflictorName()));
        }
        event.put(
            "event_context",
            "parsed from Dota replay combat log heal/resource event; exact percent unavailable"
        );
        event.put("context_confidence", "medium");
        writeEvent(event);
    }

    private void writePurchase(CombatLogEntry cle, int timestamp) throws IOException {
        Map<String, Object> event = baseEvent(timestamp, "purchase");
        event.put("item", cleanName(cle.getValueName()));
        event.put("event_context", "parsed from Dota replay combat log purchase event");
        event.put("context_confidence", "high");
        writeEvent(event);
    }

    private void writeAbility(CombatLogEntry cle, int timestamp) throws IOException {
        Map<String, Object> event = baseEvent(timestamp, "ability");
        String ability = notBlank(cle.getInflictorName()) ? cle.getInflictorName() : cle.getValueName();
        event.put("ability", cleanName(ability));
        if (cle.getAbilityLevel() > 0) {
            event.put("ability_level", cle.getAbilityLevel());
        }
        event.put("event_context", "parsed from Dota replay combat log ability/item event");
        event.put("context_confidence", "high");
        writeEvent(event);
    }

    private void writePlayerStats(CombatLogEntry cle, int timestamp) throws IOException {
        Map<String, Object> event = baseEvent(timestamp, "farm");
        if (cle.getLastHits() >= 0) {
            event.put("last_hits", cle.getLastHits());
        }
        if (cle.getNetworth() > 0) {
            event.put("networth", cle.getNetworth());
        }
        event.put(
            "event_context",
            "parsed from Dota replay playerstats combat log event; networth is not current gold"
        );
        event.put("context_confidence", "medium");
        writeEvent(event);
    }

    private void writeLevel(CombatLogEntry cle, int timestamp) throws IOException {
        Map<String, Object> event = baseEvent(timestamp, "level");
        if (cle.getValue() > 0) {
            event.put("level", cle.getValue());
        }
        event.put("event_context", "parsed from Dota replay combat log hero level event");
        event.put("context_confidence", "high");
        writeEvent(event);
    }

    private void writePosition(CombatLogEntry cle, int timestamp) throws IOException {
        Map<String, Object> event = baseEvent(timestamp, "position");
        event.put("xpos", cle.getLocationX());
        event.put("ypos", cle.getLocationY());
        event.put("event_context", "parsed from Dota replay combat log location event");
        event.put("context_confidence", "medium");
        writeEvent(event);
    }

    private void writeObjective(CombatLogEntry cle, int timestamp) throws IOException {
        Map<String, Object> event = baseEvent(timestamp, "objective");
        event.put("objective_type", cleanName(cle.getTargetName()));
        event.put("objective_team", teamName(cle.getTargetTeam()));
        event.put("attacker_team", teamName(cle.getAttackerTeam()));
        event.put("game_state", "objective_fight");
        event.put("event_context", "parsed from Dota replay combat log building objective event");
        event.put("context_confidence", "high");
        writeEvent(event);
    }

    private void writeSnapshot(int timestamp) throws IOException {
        Map<String, Object> event = baseEvent(timestamp, "snapshot");
        int fields = 0;

        Integer health = readInt(selectedHeroEntity, "m_iHealth");
        Integer maxHealth = readInt(selectedHeroEntity, "m_iMaxHealth", "m_iHealthMax");
        if (health != null) {
            fields += putField(event, "hp", health);
            putField(event, "health", health);
        }
        if (maxHealth != null && maxHealth > 0) {
            fields += putField(event, "max_hp", maxHealth);
            putField(event, "max_health", maxHealth);
        }
        if (health != null && maxHealth != null && maxHealth > 0) {
            fields += putField(event, "hp_percent", percent(health, maxHealth));
        }

        Number mana = readNumber(selectedHeroEntity, "m_flMana", "m_iMana");
        Number maxMana = readNumber(selectedHeroEntity, "m_flMaxMana", "m_iMaxMana");
        if (mana != null) {
            fields += putField(event, "mana", Math.max(0, Math.round(mana.floatValue())));
        }
        if (maxMana != null && maxMana.floatValue() > 0) {
            fields += putField(event, "max_mana", Math.max(0, Math.round(maxMana.floatValue())));
        }
        if (mana != null && maxMana != null && maxMana.floatValue() > 0) {
            fields += putField(event, "mana_percent", percent(mana.floatValue(), maxMana.floatValue()));
        }

        Integer level = readInt(selectedHeroEntity, "m_iCurrentLevel");
        if (level != null && level > 0) {
            fields += putField(event, "level", level);
        }

        Integer currentGold = readPlayerResourceInt(
            "m_vecPlayerData.%s.m_iGold",
            "m_iGold.%s"
        );
        if (currentGold != null && currentGold >= 0) {
            fields += putField(event, "gold", currentGold);
        }

        Integer totalEarnedGold = readTeamDataInt("m_iTotalEarnedGold");
        if (totalEarnedGold != null && totalEarnedGold >= 0) {
            fields += putField(event, "total_earned_gold", totalEarnedGold);
        }

        Integer lastHits = readTeamDataInt("m_iLastHitCount");
        if (lastHits != null && lastHits >= 0) {
            fields += putField(event, "last_hits", lastHits);
        }

        Integer denies = readTeamDataInt("m_iDenyCount");
        if (denies != null && denies >= 0) {
            fields += putField(event, "denies", denies);
        }

        Integer lifeState = readInt(selectedHeroEntity, "m_lifeState");
        if (lifeState != null) {
            fields += putField(event, "alive", lifeState == 0);
        }

        Number x = positionComponent(selectedHeroEntity, "X");
        Number y = positionComponent(selectedHeroEntity, "Y");
        if (x != null) {
            fields += putField(event, "xpos", rounded(x.floatValue()));
        }
        if (y != null) {
            fields += putField(event, "ypos", rounded(y.floatValue()));
        }

        if (fields == 0) {
            return;
        }

        event.put("entity_class", selectedHeroClassName);
        event.put("event_context", "parsed from Dota replay selected-hero entity snapshot");
        event.put("context_confidence", "high");
        writeEvent(event);
        snapshotCount++;
    }

    private void ensureSelectedHeroEntity() {
        if (selectedHeroEntity != null && selectedHeroEntity.isExistent()) {
            return;
        }

        Entity playerResource = entities.getByDtName("CDOTA_PlayerResource");
        if (playerResource != null) {
            resolveSelectedHeroFromPlayerResource(playerResource);
        }
        if (selectedHeroEntity == null) {
            resolveSelectedHeroByClassName();
        }
        if (selectedHeroEntity != null && options.debugEntities && !printedEntityDebug) {
            printedEntityDebug = true;
            printEntityDebug(selectedHeroEntity);
        }
    }

    private void resolveSelectedHeroFromPlayerResource(Entity playerResource) {
        if (selectedHeroFieldPath == null) {
            return;
        }
        Number handle = readNumberForFieldPath(playerResource, selectedHeroFieldPath);
        if (handle == null || handle.intValue() <= 0) {
            return;
        }
        Entity heroEntity = entities.getByHandle(handle.intValue());
        if (heroEntity == null || !isHeroEntity(heroEntity)) {
            return;
        }
        setSelectedHeroEntity(heroEntity);
    }

    private void resolveSelectedHeroByClassName() {
        Iterator<Entity> iterator = entities.getAllByPredicate(
            entity -> entity != null && isHeroEntity(entity) && matchesSelectedHero(entity.getDtClass().getDtName())
        );
        Entity match = null;
        int matches = 0;
        while (iterator.hasNext()) {
            Entity candidate = iterator.next();
            if (!candidate.isExistent()) {
                continue;
            }
            matches++;
            if (match == null) {
                match = candidate;
            }
        }
        if (matches > 1) {
            multipleMatchingHeroEntities = true;
        }
        if (match != null) {
            setSelectedHeroEntity(match);
        }
    }

    private void setSelectedHeroEntity(Entity heroEntity) {
        selectedHeroEntity = heroEntity;
        selectedHeroClassName = heroEntity.getDtClass().getDtName();
    }

    private boolean isHeroEntity(Entity entity) {
        return entity != null
            && entity.getDtClass() != null
            && entity.getDtClass().getDtName() != null
            && entity.getDtClass().getDtName().startsWith("CDOTA_Unit_Hero");
    }

    private int currentReplaySecond(Context context) {
        Integer gameTime = readGameTimeSecond();
        if (gameTime != null) {
            return gameTime;
        }
        return (int) Math.floor((context.getTick() * context.getMillisPerTick()) / 1000.0f);
    }

    private Integer readGameTimeSecond() {
        Entity rules = entities.getByDtName("CDOTAGamerulesProxy");
        if (rules == null) {
            return null;
        }
        if (gameTimePath == null) {
            gameTimePath = rules.getDtClass().getFieldPathForName("m_pGameRules.m_fGameTime");
        }
        Number gameTime = readNumberForFieldPath(rules, gameTimePath);
        if (gameTime == null) {
            return null;
        }
        return (int) Math.floor(gameTime.floatValue());
    }

    private static int playerResourceIndex(int playerSlot) {
        if (playerSlot >= 128) {
            return 5 + (playerSlot - 128);
        }
        return playerSlot;
    }

    private int selectedTeamPosition() {
        if (options.playerSlot >= 128) {
            return options.playerSlot - 128;
        }
        return options.playerSlot;
    }

    private String selectedTeamDataEntityName() {
        return options.playerSlot >= 128 ? "CDOTA_DataDire" : "CDOTA_DataRadiant";
    }

    private int putField(Map<String, Object> event, String key, Object value) {
        if (value == null) {
            return 0;
        }
        event.put(key, value);
        discoveredSnapshotFields.add(key);
        return 1;
    }

    private Integer readInt(Entity entity, String... propertyNames) {
        Number number = readNumber(entity, propertyNames);
        if (number == null) {
            return null;
        }
        return Math.round(number.floatValue());
    }

    private Number readNumber(Entity entity, String... propertyNames) {
        if (entity == null || entity.getDtClass() == null) {
            return null;
        }
        for (String propertyName : propertyNames) {
            FieldPath fieldPath = entity.getDtClass().getFieldPathForName(propertyName);
            Number number = readNumberForFieldPath(entity, fieldPath);
            if (number != null) {
                return number;
            }
        }
        return null;
    }

    private Integer readPlayerResourceInt(String... fieldPatterns) {
        Entity playerResource = entities.getByDtName("CDOTA_PlayerResource");
        if (playerResource == null) {
            return null;
        }
        String resourceIndex = Util.arrayIdxToString(playerResourceIndex(options.playerSlot));
        for (String pattern : fieldPatterns) {
            FieldPath fieldPath = playerResource.getDtClass().getFieldPathForName(format(pattern, resourceIndex));
            Number number = readNumberForFieldPath(playerResource, fieldPath);
            if (number != null) {
                return Math.round(number.floatValue());
            }
        }
        return null;
    }

    private Integer readTeamDataInt(String fieldName) {
        Entity teamData = entities.getByDtName(selectedTeamDataEntityName());
        if (teamData == null) {
            return null;
        }
        String teamPosition = Util.arrayIdxToString(selectedTeamPosition());
        FieldPath fieldPath = teamData.getDtClass().getFieldPathForName(
            format("m_vecDataTeam.%s.%s", teamPosition, fieldName)
        );
        Number number = readNumberForFieldPath(teamData, fieldPath);
        return number == null ? null : Math.round(number.floatValue());
    }

    private Number readNumberForFieldPath(Entity entity, FieldPath fieldPath) {
        if (entity == null || fieldPath == null) {
            return null;
        }
        try {
            Object value = entity.getPropertyForFieldPath(fieldPath);
            return value instanceof Number number ? number : null;
        } catch (RuntimeException exc) {
            return null;
        }
    }

    private Number positionComponent(Entity entity, String axis) {
        Number cell = readNumber(entity, "CBodyComponent.m_cell" + axis);
        Number vec = readNumber(entity, "CBodyComponent.m_vec" + axis);
        if (cell == null || vec == null) {
            return null;
        }
        return cell.floatValue() * 128.0f + vec.floatValue();
    }

    private static int percent(int value, int maxValue) {
        return percent((float) value, (float) maxValue);
    }

    private static int percent(float value, float maxValue) {
        if (maxValue <= 0) {
            return 0;
        }
        return Math.max(0, Math.min(100, Math.round((value / maxValue) * 100.0f)));
    }

    private static float rounded(float value) {
        return Math.round(value * 10.0f) / 10.0f;
    }

    private void printEntityDebug(Entity entity) {
        String[] properties = {
            "m_iHealth",
            "m_iMaxHealth",
            "m_flMana",
            "m_flMaxMana",
            "m_iCurrentLevel",
            "m_lifeState",
            "CBodyComponent.m_cellX",
            "CBodyComponent.m_vecX",
            "CBodyComponent.m_cellY",
            "CBodyComponent.m_vecY"
        };
        System.err.printf("Selected hero debug entity: index=%d handle=%d class=%s%n",
            entity.getIndex(),
            entity.getHandle(),
            entity.getDtClass().getDtName()
        );
        for (String property : properties) {
            FieldPath fieldPath = entity.getDtClass().getFieldPathForName(property);
            System.err.printf("  property %-28s available=%s%n", property, fieldPath != null);
        }
        Entity teamData = entities.getByDtName(selectedTeamDataEntityName());
        if (teamData != null) {
            String teamPosition = Util.arrayIdxToString(selectedTeamPosition());
            String[] teamFields = {
                "m_iTotalEarnedGold",
                "m_iLastHitCount",
                "m_iDenyCount"
            };
            System.err.printf(
                "Selected team data entity: class=%s position=%s%n",
                teamData.getDtClass().getDtName(),
                teamPosition
            );
            for (String field : teamFields) {
                String path = format("m_vecDataTeam.%s.%s", teamPosition, field);
                FieldPath fieldPath = teamData.getDtClass().getFieldPathForName(path);
                System.err.printf("  property %-28s available=%s%n", path, fieldPath != null);
            }
        }
    }

    private Map<String, Object> baseEvent(int timestamp, String eventType) {
        Map<String, Object> event = new LinkedHashMap<>();
        event.put("timestamp_seconds", timestamp);
        event.put("minute", timestamp / 60);
        event.put("event_type", eventType);
        event.put("type", eventType);
        event.put("hero", options.hero);
        event.put("player_slot", options.playerSlot);
        return event;
    }

    private void writeEvent(Map<String, Object> event) throws IOException {
        writer.write(toJson(event));
        writer.newLine();
        eventCount++;
    }

    private boolean isSelectedTarget(CombatLogEntry cle) {
        return matchesSelectedHero(cle.getTargetName());
    }

    private boolean isSelectedActor(CombatLogEntry cle) {
        return matchesSelectedHero(cle.getAttackerName()) || matchesSelectedHero(cle.getTargetName());
    }

    private boolean matchesSelectedHero(String value) {
        if (!notBlank(value)) {
            return false;
        }
        String normalizedValue = normalizeToken(value);
        String normalizedHero = normalizeToken(options.hero);
        return normalizedValue.equals(normalizedHero)
            || normalizedValue.contains(normalizedHero)
            || normalizedHero.contains(normalizedValue);
    }

    private static String normalizeToken(String value) {
        String normalized = value == null ? "" : value.toLowerCase(Locale.ROOT);
        normalized = normalized.replace("npc_dota_hero_", "");
        normalized = normalized.replace("item_", "");
        return normalized.replaceAll("[^a-z0-9]+", "");
    }

    private static String cleanName(String raw) {
        if (!notBlank(raw)) {
            return "";
        }
        String value = raw.trim();
        value = value.replace("npc_dota_hero_", "");
        value = value.replace("item_", "");
        value = value.replace('_', ' ');
        String[] parts = value.split("\\s+");
        StringBuilder result = new StringBuilder();
        for (String part : parts) {
            if (part.isEmpty()) {
                continue;
            }
            if (result.length() > 0) {
                result.append(' ');
            }
            if (part.length() <= 3 && part.equals(part.toUpperCase(Locale.ROOT))) {
                result.append(part);
            } else {
                result.append(Character.toUpperCase(part.charAt(0)));
                if (part.length() > 1) {
                    result.append(part.substring(1).toLowerCase(Locale.ROOT));
                }
            }
        }
        return result.toString();
    }

    private static String teamName(int team) {
        if (team == 2) {
            return "radiant";
        }
        if (team == 3) {
            return "dire";
        }
        return String.valueOf(team);
    }

    private static boolean notBlank(String value) {
        return value != null && !value.trim().isEmpty();
    }

    private static String toJson(Object value) {
        if (value == null) {
            return "null";
        }
        if (value instanceof String stringValue) {
            return "\"" + escapeJson(stringValue) + "\"";
        }
        if (value instanceof Number || value instanceof Boolean) {
            return String.valueOf(value);
        }
        if (value instanceof Map<?, ?> map) {
            StringBuilder builder = new StringBuilder("{");
            boolean first = true;
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                Object entryValue = entry.getValue();
                if (entryValue == null) {
                    continue;
                }
                if (!first) {
                    builder.append(',');
                }
                builder.append(toJson(String.valueOf(entry.getKey())));
                builder.append(':');
                builder.append(toJson(entryValue));
                first = false;
            }
            builder.append('}');
            return builder.toString();
        }
        return toJson(String.valueOf(value));
    }

    private static String escapeJson(String value) {
        StringBuilder builder = new StringBuilder();
        for (int i = 0; i < value.length(); i++) {
            char ch = value.charAt(i);
            switch (ch) {
                case '"':
                    builder.append("\\\"");
                    break;
                case '\\':
                    builder.append("\\\\");
                    break;
                case '\b':
                    builder.append("\\b");
                    break;
                case '\f':
                    builder.append("\\f");
                    break;
                case '\n':
                    builder.append("\\n");
                    break;
                case '\r':
                    builder.append("\\r");
                    break;
                case '\t':
                    builder.append("\\t");
                    break;
                default:
                    if (ch < 0x20) {
                        builder.append(String.format("\\u%04x", (int) ch));
                    } else {
                        builder.append(ch);
                    }
                    break;
            }
        }
        return builder.toString();
    }

    private static final class Options {
        private boolean help;
        private Path demo;
        private Path output;
        private String hero;
        private int playerSlot;
        private int startSeconds = 0;
        private int endSeconds = Integer.MAX_VALUE;
        private int snapshotIntervalSeconds = 1;
        private boolean debugEntities;

        private static Options parse(String[] args) {
            Options options = new Options();
            for (int i = 0; i < args.length; i++) {
                String arg = args[i];
                switch (arg) {
                    case "--help":
                    case "-h":
                        options.help = true;
                        return options;
                    case "--demo":
                        options.demo = Path.of(requireValue(args, ++i, arg));
                        break;
                    case "--output":
                        options.output = Path.of(requireValue(args, ++i, arg));
                        break;
                    case "--hero":
                        options.hero = requireValue(args, ++i, arg);
                        break;
                    case "--player-slot":
                        options.playerSlot = Integer.parseInt(requireValue(args, ++i, arg));
                        break;
                    case "--start":
                        options.startSeconds = Integer.parseInt(requireValue(args, ++i, arg));
                        break;
                    case "--end":
                        options.endSeconds = Integer.parseInt(requireValue(args, ++i, arg));
                        break;
                    case "--snapshot-interval":
                        options.snapshotIntervalSeconds = Integer.parseInt(requireValue(args, ++i, arg));
                        break;
                    case "--debug-entities":
                        options.debugEntities = true;
                        break;
                    default:
                        throw new IllegalArgumentException("Unknown argument: " + arg);
                }
            }
            options.validate();
            return options;
        }

        private static String requireValue(String[] args, int index, String arg) {
            if (index >= args.length) {
                throw new IllegalArgumentException("Missing value for " + arg);
            }
            return args[index];
        }

        private void validate() {
            if (demo == null) {
                throw new IllegalArgumentException("--demo is required");
            }
            if (output == null) {
                throw new IllegalArgumentException("--output is required");
            }
            if (!Files.exists(demo)) {
                throw new IllegalArgumentException("Demo file not found: " + demo);
            }
            if (!notBlank(hero)) {
                throw new IllegalArgumentException("--hero is required");
            }
            if (endSeconds < startSeconds) {
                throw new IllegalArgumentException("--end must be greater than or equal to --start");
            }
            if (snapshotIntervalSeconds < 1) {
                throw new IllegalArgumentException("--snapshot-interval must be >= 1");
            }
        }

        private static void printUsage() {
            System.out.println(
                "Usage: java -jar dota-replay-events.jar " +
                "--demo replay.dem --hero \"Juggernaut\" --player-slot 1 " +
                "--start 0 --end 600 --snapshot-interval 1 --output replay_events.jsonl"
            );
        }
    }
}
