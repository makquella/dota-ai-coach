"use strict";

// Match-detail composition is separate from career/profile and request owners.
// Cards/DOM/action ports stay explicit; this controller neither fetches data nor
// owns navigation/account state. Caller supplies the accepted current detail.
(function () {
  function create(ports) {
    const {
      reviewBackButton, h, neighbourButtons, shareButton, pdfButton, card, t,
      skeletonRows, hydrate, tOptional, emptyState, openMatch, getMatchId, icon,
      reviewHeader, toolbarMatch, zone, coachCard, focusCard, findingsCard, askCard,
      chartCard, laneCard, deathsCard, adviceLogCard, sectionsCard, rankCard,
      draftCard, mapCard, buildCard, skillsCard, momentsCard, twoColumns,
      scoreboardCard, sectionNav, stickToolbar, watchSections, drawMatchCharts
    } = ports;
    function draw({root, detail}) {
      const backButton = reviewBackButton();
      const sharePanel = h("section", { class: "card share-panel no-print", hidden: true });
      const back = h(
        "div",
        { class: "review-toolbar no-print" },
        h("span", { class: "review-nav" }, backButton, neighbourButtons()),
        detail && detail.analysis
          ? h("span", { class: "toolbar-actions" }, shareButton(sharePanel, detail), pdfButton("match"))
          : null
      );
      if (!detail) {
        root.replaceChildren(back, card(t("reviewLoading"), "activity", skeletonRows(6)));
        hydrate(root);
        return;
      }
      if (detail.error) {
        // A readable reason and a retry, never the bare code («request_failed»).
        const reason = tOptional(`matchErrors.${detail.error}`) || t("matchErrors.request_failed");
        const retry = detail.error === "match_not_found" ? null : h("button", { class: "btn btn-sm", type: "button", onclick: () => openMatch(getMatchId()) }, icon("refresh-cw"), h("span", { text: t("reviewRetry") }));
        root.replaceChildren(back, card(t("reviewError"), "circle-alert", emptyState("circle-alert", reason, "", retry)));
        hydrate(root);
        return;
      }
      const analysis = detail.analysis;
      const summary = detail.summary || {};
      const header = reviewHeader(detail, analysis, summary);
      back.insertBefore(toolbarMatch(detail, analysis, summary), back.children[1] || null);
      const parts = [back, sharePanel, header];
      if (!analysis) {
        parts.push(card(t("reviewLoading"), "hourglass", emptyState("hourglass", t("reviewPending"), tOptional(`parseStatus.${detail.parse_status}`) || "")));
      } else {
        // The story of the match on the left, the side facts on the right (one
        // column in a narrow window, main first).
        const main = [];
        const side = [];
        const add = (list, element) => {
          if (element) {
            list.push(element);
          }
        };
        // Zones: what to fix first, then how the match went; on the side the
        // scores and comparisons, then the map and the items.
        const rest = (analysis.improvements || []).filter((f) => !(analysis.focus || []).includes(f.id));
        add(main, zone(t("zoneFix"), t("zoneFixHint"), [
          coachCard(detail.coach, "match"),
          focusCard(analysis, detail),
          // Past «what to fix first» the rest starts folded: a first review
          // was a wall of lists.
          rest.length ? findingsCard(t("improveTitle"), "target", rest, "", true, detail.repeats, 1) : null,
          askCard(detail)
        ], { id: "fix", label: t("navFix") }));
        add(main, zone(t("zoneStory"), t("zoneStoryHint"), [chartCard(analysis), laneCard(analysis), deathsCard(analysis), adviceLogCard(analysis)], { id: "story", label: t("navStory") }));
        add(side, zone(t("zoneScores"), t("zoneScoresHint"), [
          sectionsCard(analysis),
          findingsCard(t("strengthsTitle"), "sparkles", analysis.strengths, t("nothingStrong"), false),
          rankCard(analysis),
          draftCard(analysis)
        ], { id: "scores", label: t("navScores") }));
        add(side, zone(t("zoneMapItems"), t("zoneMapItemsHint"), [mapCard(analysis), buildCard(analysis), skillsCard(analysis), momentsCard(analysis)], { id: "map", label: t("navMap") }));
        parts.push(twoColumns(main, side));
      }
      if (detail.scoreboard) {
        parts.push(zone(t("zoneTeams"), "", [scoreboardCard(detail.scoreboard)], { id: "teams", label: t("navTeams") }));
      }
      root.replaceChildren(...parts);
      // The zone links sit in the sticky bar, before «Share · Save PDF».
      const nav = sectionNav(root);
      if (nav) {
        back.insertBefore(nav, back.querySelector(".toolbar-actions"));
      }
      hydrate(root);
      stickToolbar(back, header);
      watchSections(nav);
      // Charts measure their container, so draw after insertion.
      drawMatchCharts(root, analysis);
    }

    return {draw};
  }
  const api = {create};
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else window.WardlyMatchDetail = api;
})();
