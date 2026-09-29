// Mockup interaction: the plate and the caption change together. No framework.
(() => {
  const root = document.documentElement;
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  let activeFace = 'front';

  // Faces: click to activate; the notes column says which side it edits.
  $$('.face-slot').forEach(slot => slot.addEventListener('click', () => {
    $$('.face-slot').forEach(s => { s.classList.toggle('is-active', s === slot); s.setAttribute('aria-pressed', s === slot); });
    activeFace = slot.dataset.face;
    $('#editing-face').textContent = activeFace === 'front' ? 'obverse' : 'reverse';
    syncInputs();
  }));

  const state = {
    front: { top: 'NORTHERN ANALYSIS UNIT', bottom: 'Est. 2021' },
    back: { top: 'STRENGTH THROUGH DATA', bottom: 'Presented for service' },
  };
  function syncInputs() {
    $('#f-top').value = state[activeFace].top;
    $('#f-bottom').value = state[activeFace].bottom;
  }

  // Inscription: retype and the arc text redraws on the active face.
  ['top', 'bottom'].forEach(slot => {
    $(`[data-bind="${slot}"]`).addEventListener('input', e => {
      state[activeFace][slot] = e.target.value;
      $(`#${activeFace} [data-slot="${slot}"]`).textContent = e.target.value;
      updateCondition();
    });
  });
  $('[data-bind="size"]').addEventListener('input', e => $$('.inscription').forEach(t => t.setAttribute('font-size', e.target.value)));
  $('[data-bind="spacing"]').addEventListener('input', e => $$('.inscription').forEach(t => t.setAttribute('letter-spacing', e.target.value)));

  // Caption facts follow the notes.
  const cap = (k, v) => { const el = $(`[data-cap="${k}"]`); if (el) el.textContent = v; };
  ['diameter', 'body', 'relief'].forEach(k => $(`[data-bind="${k}"]`).addEventListener('input', e => cap(k, e.target.value)));
  $('[data-bind="teeth"]').addEventListener('input', e => cap('edge', `reeded edge, ${e.target.value} teeth`));
  $('[data-bind="dots"]').addEventListener('change', e => $$('.coin').forEach(c => c.classList.toggle('no-dots', !e.target.checked)));

  // Filament swatches recolour the coin and rewrite the caption in one go.
  $$('.swatches').forEach(group => group.addEventListener('click', e => {
    const b = e.target.closest('[role="radio"]'); if (!b) return;
    $$('[role="radio"]', group).forEach(x => x.setAttribute('aria-checked', x === b));
    const role = group.dataset.role;
    if (role === 'relief') { root.style.setProperty('--relief', b.dataset.hex); cap('relief-filament', b.dataset.name); }
    if (role === 'enamel-front') { root.style.setProperty('--enamel', b.dataset.hex); cap('enamel-front', b.dataset.name); }
    if (role === 'enamel-back') { root.style.setProperty('--enamel-back', b.dataset.hex); }
  }));

  // Edge and preset: one pull regathers the coin.
  function setEdge(edge) {
    $$('.coin').forEach(c => c.classList.toggle('is-plain', edge === 'plain'));
    $$('[data-edge]').forEach(x => x.setAttribute('aria-checked', x.dataset.edge === edge));
    cap('edge', edge === 'plain' ? 'plain edge' : `reeded edge, ${$('[data-bind="teeth"]').value} teeth`);
    $('#f-teeth').disabled = edge === 'plain';
  }
  $$('[data-edge]').forEach(b => b.addEventListener('click', () => setEdge(b.dataset.edge)));
  $$('input[name="preset"]').forEach(r => r.addEventListener('change', () => {
    const fancy = r.value === 'fancy';
    setEdge(fancy ? 'reeded' : 'plain');
    $('[data-bind="dots"]').checked = fancy;
    $$('.coin').forEach(c => c.classList.toggle('no-dots', !fancy));
    $('.preset-hint').textContent = fancy ? 'Reeded edge, separator dots, inner ring' : 'Plain edge, no dots, wider text';
  }));

  // Condition report: one honest example rule, so the state grammar is visible.
  function updateCondition() {
    const long = state.front.bottom.length > 24 || state.back.bottom.length > 24;
    const list = $('.condition-list');
    let li = $('[data-note="length"]', list);
    if (long && !li) {
      li = document.createElement('li'); li.dataset.note = 'length';
      li.innerHTML = '<span class="mark" aria-hidden="true">⚑</span>Bottom text over 24 characters will overlap the top arc at this size. Shorten it or reduce Size. <button type="button" class="link small">Acknowledge</button>';
      list.appendChild(li);
    } else if (!long && li) li.remove();
    $('#condition').dataset.count = list.children.length;
  }
  $$('.condition-list').forEach(l => l.addEventListener('click', e => {
    if (e.target.matches('button')) { e.target.closest('li').remove(); $('#condition').dataset.count = l.children.length; }
  }));

  // Lot name becomes the file name.
  $('#lot-name').addEventListener('input', e => {
    $('#file-slug').textContent = e.target.textContent.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '') || 'coin';
  });
})();
