/*
 * Máscaras de campos de identificação (HANDOFF_CLAUDE_CODE.md, seção 6).
 * Usa IMask (app/static/js/vendor/imask.min.js, vendorizado para funcionar
 * mesmo sem internet na rede do escritório).
 *
 * Uso: adicionar data-mask="<tipo>" no <input>. Tipos disponíveis:
 * cpf, cnpj, cei, cno, caepf, telefone, cep, moeda, ie (com
 * data-uf-campo="<id do <select> de UF>" — GO usa máscara fixa, outros
 * estados ficam livres, já que os formatos variam por UF).
 */
(function () {
  const DEFINICOES_ALFANUMERICO = { "#": /[A-Za-z0-9]/ };

  function aplicarCpf(el) {
    return IMask(el, { mask: "000.000.000-00" });
  }

  function aplicarCnpj(el) {
    return IMask(el, {
      mask: "##.###.###/####-00",
      definitions: DEFINICOES_ALFANUMERICO,
      prepare: (str) => str.toUpperCase(),
    });
  }

  function aplicarCeiCno(el) {
    return IMask(el, { mask: "00.000.00000/00" });
  }

  function aplicarCaepf(el) {
    return IMask(el, { mask: "00.000.000/0000-00" });
  }

  function aplicarTelefone(el) {
    return IMask(el, {
      mask: [{ mask: "(00) 0000-0000" }, { mask: "(00) 00000-0000" }],
    });
  }

  function aplicarCep(el) {
    return IMask(el, { mask: "00000-000" });
  }

  function aplicarMoeda(el) {
    return IMask(el, {
      mask: Number,
      scale: 2,
      thousandsSeparator: ".",
      radix: ",",
      mapToRadix: [","],
      normalizeZeros: true,
      padFractionalZeros: true,
    });
  }

  function aplicarIeGo(el) {
    return IMask(el, { mask: "00.000.000-0" });
  }

  // Inscrição estadual: formato varia por UF — só trava a máscara para GO
  // (a única confirmada até aqui); demais estados ficam em texto livre.
  function configurarMascaraIe(el) {
    const campoUfId = el.dataset.ufCampo;
    const campoUf = campoUfId ? document.getElementById(campoUfId) : null;
    let instancia = null;

    function atualizar() {
      const uf = (campoUf && campoUf.value) || "";
      if (instancia) {
        instancia.destroy();
        instancia = null;
      }
      if (uf.toUpperCase() === "GO") {
        instancia = aplicarIeGo(el);
      }
    }

    atualizar();
    if (campoUf) campoUf.addEventListener("change", atualizar);
  }

  // CNPJ/CPF: o mesmo campo "cnpj" guarda um documento ou outro conforme
  // tipo_inscricao (ver app/models/empresa.py).
  function configurarMascaraCnpjCpf(el) {
    const campoTipoId = el.dataset.tipoCampo;
    const campoTipo = campoTipoId ? document.getElementById(campoTipoId) : null;
    let instancia = null;

    function atualizar() {
      const tipo = (campoTipo && campoTipo.value) || "CNPJ";
      if (instancia) {
        instancia.destroy();
        instancia = null;
      }
      instancia = tipo === "CPF" ? aplicarCpf(el) : aplicarCnpj(el);
    }

    atualizar();
    if (campoTipo) campoTipo.addEventListener("change", atualizar);
  }

  const APLICADORES = {
    cpf: aplicarCpf,
    cnpj: aplicarCnpj,
    cei: aplicarCeiCno,
    cno: aplicarCeiCno,
    caepf: aplicarCaepf,
    telefone: aplicarTelefone,
    cep: aplicarCep,
    moeda: aplicarMoeda,
  };

  document.addEventListener("DOMContentLoaded", function () {
    if (typeof IMask === "undefined") return;

    document.querySelectorAll("[data-mask]").forEach(function (el) {
      const tipo = el.dataset.mask;
      if (tipo === "ie") {
        configurarMascaraIe(el);
      } else if (tipo === "cnpj-cpf") {
        configurarMascaraCnpjCpf(el);
      } else if (APLICADORES[tipo]) {
        APLICADORES[tipo](el);
      }
    });
  });
})();
