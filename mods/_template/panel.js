(function () {
  if (!window.NebulaMods || typeof window.NebulaMods.register !== 'function') return;

  // Rename 'my_mod' below to match your mod.json "id" after copying _template/
  const MOD_ID = 'my_mod';

  function esc(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  window.NebulaMods.register(MOD_ID, function mountTemplateMod(container, bridge) {
    const state = {
      profiles: [],
      tagsByProfile: {},
      selectedProfileId: bridge.context && bridge.context.profile_id ? String(bridge.context.profile_id) : '',
      busy: false
    };

    const $ = (sel) => container.querySelector(sel);
    const $$ = (sel) => Array.from(container.querySelectorAll(sel));

    function setBusy(flag) {
      state.busy = flag;
      $$('button[data-action]').forEach((btn) => { btn.disabled = flag; });
    }

    function syncFormFromSelected() {
      const pid = Number(state.selectedProfileId || 0);
      const item = state.tagsByProfile[pid] || null;
      const tagInput = $('[data-tag-input]');
      const noteInput = $('[data-note-input]');
      if (tagInput) tagInput.value = item ? (item.tag || '') : '';
      if (noteInput) noteInput.value = item ? (item.note || '') : '';
    }

    function renderProfiles() {
      const sel = $('[data-profile-select]');
      if (!sel) return;
      if (!state.profiles.length) {
        sel.innerHTML = '<option value="">暂无指纹环境，请先在主界面创建环境</option>';
        state.selectedProfileId = '';
        syncFormFromSelected();
        return;
      }
      sel.innerHTML = state.profiles.map((p) => {
        const label = [p.code || ('#' + p.id), p.name || '未命名'].join(' · ');
        return '<option value="' + esc(p.id) + '">' + esc(label) + '</option>';
      }).join('');
      if (state.selectedProfileId && state.profiles.some((p) => String(p.id) === String(state.selectedProfileId))) {
        sel.value = String(state.selectedProfileId);
      } else {
        state.selectedProfileId = String(state.profiles[0].id);
        sel.value = state.selectedProfileId;
      }
      syncFormFromSelected();
    }

    function renderTable() {
      const tbody = $('[data-tags-tbody]');
      const badge = $('[data-count-badge]');
      const items = Object.values(state.tagsByProfile);
      if (badge) badge.textContent = items.length + ' 条';
      if (!tbody) return;
      if (!items.length) {
        tbody.innerHTML = '<tr><td colspan="4" class="tplmod-empty">尚未保存任何环境标签</td></tr>';
        return;
      }
      const profileMap = {};
      state.profiles.forEach((p) => { profileMap[p.id] = p; });
      tbody.innerHTML = items.map((item) => {
        const p = profileMap[item.profile_id];
        const envLabel = p ? (p.code || ('#' + p.id)) : ('#' + item.profile_id);
        return (
          '<tr data-row-pid="' + esc(item.profile_id) + '">' +
            '<td class="mono">' + esc(envLabel) + '</td>' +
            '<td><span class="badge badge-sky">' + esc(item.tag || '已打卡') + '</span></td>' +
            '<td class="mono">' + esc(item.stamp_count || 0) + '</td>' +
            '<td>' + esc(item.note || '-') + '</td>' +
          '</tr>'
        );
      }).join('');
    }

    async function loadOverview() {
      setBusy(true);
      try {
        const data = await bridge.invoke('get_overview', {});
        state.profiles = Array.isArray(data.profiles) ? data.profiles : [];
        state.tagsByProfile = {};
        (data.tags || []).forEach((item) => {
          state.tagsByProfile[Number(item.profile_id)] = item;
        });
        const meta = $('[data-runtime-meta]');
        if (meta) {
          meta.textContent = 'Mod: ' + (data.mod_id || MOD_ID) +
            ' · Nebula v' + (data.app_version || '-') +
            ' · OS: ' + (data.host_os || '-');
        }
        renderProfiles();
        renderTable();
      } catch (err) {
        bridge.toast(err.message || '加载扩展数据失败', 'error');
      } finally {
        setBusy(false);
      }
    }

    async function handleClick(ev) {
      const btn = ev.target.closest('button[data-action]');
      if (!btn || state.busy) return;
      const act = btn.dataset.action;

      if (act === 'reload') {
        await loadOverview();
        return;
      }
      if (!state.selectedProfileId) {
        bridge.toast('请先选择一个目标指纹环境', 'warning');
        return;
      }

      setBusy(true);
      try {
        if (act === 'save') {
          const tag = ($('[data-tag-input]') || {}).value || '';
          const note = ($('[data-note-input]') || {}).value || '';
          await bridge.invoke('save_tag', {
            profile_id: Number(state.selectedProfileId),
            tag: tag.trim(),
            note: note.trim()
          });
          bridge.toast('扩展标签已保存到加密工作区', 'success');
        } else if (act === 'stamp') {
          const res = await bridge.invoke('quick_stamp_profile', {
            profile_id: Number(state.selectedProfileId)
          });
          bridge.toast((res && res.message) || '打卡成功', 'success');
        } else if (act === 'delete') {
          await bridge.invoke('delete_tag', {
            profile_id: Number(state.selectedProfileId)
          });
          bridge.toast('已清除该环境的扩展标签', 'info');
        }
        await loadOverview();
        if (typeof bridge.refreshProfiles === 'function') {
          await bridge.refreshProfiles();
        }
      } catch (err) {
        bridge.toast(err.message || '操作失败', 'error');
      } finally {
        setBusy(false);
      }
    }

    function handleSelectChange(ev) {
      if (ev.target.matches('[data-profile-select]')) {
        state.selectedProfileId = ev.target.value;
        syncFormFromSelected();
      }
    }

    container.addEventListener('click', handleClick);
    container.addEventListener('change', handleSelectChange);
    loadOverview();

    return {
      destroy() {
        container.removeEventListener('click', handleClick);
        container.removeEventListener('change', handleSelectChange);
      }
    };
  });
})();
