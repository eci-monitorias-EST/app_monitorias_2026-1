function doPost(e) {
  try {
    const CONFIG = {
      token: "bankify_monitorias_2026_sync_9c7f1a42",
      spreadsheetId: "1ufR3nbA4jnxWaed2JUazdhduMCIM_PvWtwAJnexp4V4",
      sheets: {
        sesiones: "sesiones",
        respuestas: "respuestas",
        historialComentarios: "historial_comentarios",
        feedback: "feedback",
        control: "control_ingreso"
      }
    };

    const data = parseBody_(e);
    if (String(data.token || "") !== CONFIG.token) {
      return jsonResponse_({ status: "error", message: "No autorizado" });
    }

    const ss = SpreadsheetApp.openById(CONFIG.spreadsheetId);
    const sheets = ensureSheets_(ss, CONFIG.sheets);
    const action = String(data.accion || "").toLowerCase();

    if (action === "upsert_sesion" || action === "bienvenida" || action === "actualizar_bienvenida") {
      const payload = normalizeSessionPayload_(data);
      validateRequired_(payload, ["participant_id", "public_alias"]);
      const result = upsertByKey_(
        sheets.sesiones,
        ["participant_id"],
        payload,
        [
          "participant_id",
          "public_alias",
          "Dia",
          "nombre",
          "sexo",
          "colegio",
          "edad",
          "grado",
          "interes_carrera",
          "matematicas_avanzadas",
          "is_test_data",
          "test_batch_id",
          "data_origin",
          "updated_at"
        ]
      );
      upsertByKey_(
        sheets.control,
        ["participant_id", "exercise"],
        {
          participant_id: payload.participant_id,
          exercise: "session",
          status: "active",
          is_test_data: payload.is_test_data,
          test_batch_id: payload.test_batch_id,
          data_origin: payload.data_origin,
          updated_at: payload.updated_at
        },
        ["participant_id", "exercise", "status", "is_test_data", "test_batch_id", "data_origin", "updated_at"]
      );
      return jsonResponse_({ status: "success", action: action, mode: result.mode, participant_id: payload.participant_id });
    }

    if (action === "upsert_respuesta" || action === "ejercicio" || action === "actualizar_ejercicio") {
      const payload = normalizeProgressPayload_(data);
      validateRequired_(payload, ["participant_id", "exercise"]);
      upsertCommentHistory_(sheets.historialComentarios, payload);
      const result = upsertByKey_(
        sheets.respuestas,
        ["participant_id", "exercise"],
        payload,
        [
          "participant_id",
          "exercise",
          "dataset_comment",
          "analytics_comment",
          "prediction_reflection",
          "prediction_inputs",
          "prediction_output",
          "is_test_data",
          "test_batch_id",
          "data_origin",
          "updated_at"
        ]
      );
      return jsonResponse_({ status: "success", action: action, mode: result.mode, participant_id: payload.participant_id, exercise: payload.exercise });
    }

    if (action === "upsert_feedback" || action === "retroalimentacion" || action === "actualizar_retroalimentacion") {
      const payload = normalizeFeedbackPayload_(data);
      validateRequired_(payload, ["participant_id", "exercise"]);
      const result = upsertByKey_(
        sheets.feedback,
        ["participant_id", "exercise"],
        payload,
        ["participant_id", "exercise", "rating", "summary", "missing_topics", "improvement_ideas", "is_test_data", "test_batch_id", "data_origin", "updated_at"]
      );
      return jsonResponse_({ status: "success", action: action, mode: result.mode, participant_id: payload.participant_id, exercise: payload.exercise });
    }

    if (action === "marcar_completado") {
      const payload = {
        participant_id: String(data.participant_id || data.id || "").trim(),
        exercise: String(data.exercise || data.ejercicio || "").trim(),
        status: "completed",
        is_test_data: normalizeTraceabilityFields_(data).is_test_data,
        test_batch_id: normalizeTraceabilityFields_(data).test_batch_id,
        data_origin: normalizeTraceabilityFields_(data).data_origin,
        updated_at: isoNow_()
      };
      validateRequired_(payload, ["participant_id", "exercise"]);
      const result = upsertByKey_(
        sheets.control,
        ["participant_id", "exercise"],
        payload,
        ["participant_id", "exercise", "status", "is_test_data", "test_batch_id", "data_origin", "updated_at"]
      );
      return jsonResponse_({ status: "success", action: action, mode: result.mode, participant_id: payload.participant_id, exercise: payload.exercise });
    }

    if (action === "get_test_batch") {
      const testBatchId = String(data.test_batch_id || "").trim();
      const exercise = String(data.exercise || "").trim();
      validateRequired_({ test_batch_id: testBatchId }, ["test_batch_id"]);
      return jsonResponse_({
        status: "success",
        action: action,
        test_batch_id: testBatchId,
        sesiones: getRowsByTestBatch_(sheets.sesiones, testBatchId, ""),
        respuestas: getRowsByTestBatch_(sheets.respuestas, testBatchId, exercise),
        historial_comentarios: getRowsByTestBatch_(sheets.historialComentarios, testBatchId, exercise),
        feedback: getRowsByTestBatch_(sheets.feedback, testBatchId, exercise),
        control: getRowsByTestBatch_(sheets.control, testBatchId, exercise)
      });
    }

    if (action === "delete_test_batch") {
      const testBatchId = String(data.test_batch_id || "").trim();
      const dryRun = normalizeBoolean_(data.dry_run, true);
      const confirmPhrase = String(data.confirm_phrase || "").trim();
      validateRequired_({ test_batch_id: testBatchId }, ["test_batch_id"]);
      if (!dryRun && confirmPhrase !== "DELETE_TEST_BATCH") {
        throw new Error("Borrado rechazado: confirm_phrase inválido para delete_test_batch");
      }
      const deleteResult = deleteRowsByTestBatch_(sheets, testBatchId, dryRun);
      return jsonResponse_(deleteResult);
    }

    return jsonResponse_({ status: "error", message: "Acción no válida" });
  } catch (error) {
    return jsonResponse_({ status: "error", message: String(error) });
  }
}

function parseBody_(e) {
  if (!e || !e.postData || !e.postData.contents) {
    throw new Error("No llegó contenido en el body");
  }
  return JSON.parse(e.postData.contents);
}

function ensureSheets_(ss, sheetMap) {
  const output = {};
  Object.keys(sheetMap).forEach(function(key) {
    const name = sheetMap[key];
    let sheet = ss.getSheetByName(name);
    if (!sheet) {
      sheet = ss.insertSheet(name);
    }
    output[key] = sheet;
  });
  return output;
}

function normalizeSessionPayload_(data) {
  const profile = data.profile || {};
  const traceability = normalizeTraceabilityFields_(data);
  return {
    participant_id: String(data.participant_id || data.id || "").trim(),
    public_alias: String(data.public_alias || "").trim(),
    Dia: String(data.Dia || profile.Dia || isoDateNow_()).trim(),
    nombre: String(profile.nombre || profile.name || data.nombre || "").trim(),
    sexo: String(profile.sexo || data.sexo || "").trim(),
    colegio: String(profile.colegio || profile.institution || data.colegio || "").trim(),
    edad: Number(profile.edad || data.edad || 0),
    grado: String(profile.grado || data.grado || "").trim(),
    interes_carrera: String(profile.interes_carrera || data.interes_carrera || "").trim(),
    matematicas_avanzadas: String(
      profile.matematicas_avanzadas || data.matematicas_avanzadas || ""
    ).trim(),
    is_test_data: traceability.is_test_data,
    test_batch_id: traceability.test_batch_id,
    data_origin: traceability.data_origin,
    updated_at: isoNow_()
  };
}

function normalizeProgressPayload_(data) {
  const payload = data.payload || {};
  const traceability = normalizeTraceabilityFields_(data);
  return {
    participant_id: String(data.participant_id || data.id || "").trim(),
    exercise: String(data.exercise || data.ejercicio || "").trim(),
    dataset_comment: String(payload.dataset_comment || data.comentario || "").trim(),
    analytics_comment: String(payload.analytics_comment || "").trim(),
    prediction_reflection: String(payload.prediction_reflection || "").trim(),
    prediction_inputs: JSON.stringify(payload.prediction_inputs || {}),
    prediction_output: JSON.stringify(payload.prediction_output || {}),
    is_test_data: traceability.is_test_data,
    test_batch_id: traceability.test_batch_id,
    data_origin: traceability.data_origin,
    updated_at: isoNow_()
  };
}

function normalizeFeedbackPayload_(data) {
  const payload = data.payload || {};
  const traceability = normalizeTraceabilityFields_(data);
  return {
    participant_id: String(data.participant_id || data.id || "").trim(),
    exercise: String(data.exercise || data.ejercicio || "").trim(),
    rating: Number(payload.rating || 0),
    summary: String(payload.summary || data.que_parecio || "").trim(),
    missing_topics: String(payload.missing_topics || data.que_hubiera_gustado || "").trim(),
    improvement_ideas: String(payload.improvement_ideas || data.cosas_mejorar || "").trim(),
    is_test_data: traceability.is_test_data,
    test_batch_id: traceability.test_batch_id,
    data_origin: traceability.data_origin,
    updated_at: isoNow_()
  };
}

function normalizeTraceabilityFields_(data) {
  const testBatchId = String(data.test_batch_id || "").trim();
  return {
    is_test_data: normalizeBoolean_(data.is_test_data, testBatchId !== ""),
    test_batch_id: testBatchId,
    data_origin: String(data.data_origin || (testBatchId ? "synthetic_mass_imputation" : "app_runtime")).trim()
  };
}

function validateRequired_(payload, fields) {
  const missing = fields.filter(function(field) {
    return !String(payload[field] || "").trim();
  });
  if (missing.length > 0) {
    throw new Error("Faltan campos requeridos: " + missing.join(", "));
  }
}

function upsertCommentHistory_(sheet, payload) {
  const hasComments = [
    payload.dataset_comment,
    payload.analytics_comment,
    payload.prediction_reflection
  ].some(function(value) {
    return String(value || "").trim() !== "";
  });

  if (!hasComments) {
    return;
  }

  const columns = [
    "participant_id",
    "exercise",
    "dataset_comment",
    "analytics_comment",
    "prediction_reflection",
    "prediction_inputs",
    "prediction_output",
    "is_test_data",
    "test_batch_id",
    "data_origin",
    "captured_at"
  ];

  upsertByKey_(
    sheet,
    ["participant_id", "exercise"],
    {
      participant_id: payload.participant_id,
      exercise: payload.exercise,
      dataset_comment: payload.dataset_comment,
      analytics_comment: payload.analytics_comment,
      prediction_reflection: payload.prediction_reflection,
      prediction_inputs: payload.prediction_inputs,
      prediction_output: payload.prediction_output,
      is_test_data: payload.is_test_data,
      test_batch_id: payload.test_batch_id,
      data_origin: payload.data_origin,
      captured_at: isoNow_()
    },
    columns
  );
}

function getRowsByTestBatch_(sheet, testBatchId, exercise) {
  const rows = getSheetRows_(sheet);
  return rows.filter(function(row) {
    if (!rowMatchesTestBatch_(row, testBatchId)) {
      return false;
    }
    if (!exercise) {
      return true;
    }
    return String(row.exercise || "").trim() === exercise;
  });
}

function deleteRowsByTestBatch_(sheets, testBatchId, dryRun) {
  const lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    const results = {
      sesiones: deleteRowsInSheetByTestBatch_(sheets.sesiones, testBatchId, dryRun),
      respuestas: deleteRowsInSheetByTestBatch_(sheets.respuestas, testBatchId, dryRun),
      historial_comentarios: deleteRowsInSheetByTestBatch_(sheets.historialComentarios, testBatchId, dryRun),
      feedback: deleteRowsInSheetByTestBatch_(sheets.feedback, testBatchId, dryRun),
      control: deleteRowsInSheetByTestBatch_(sheets.control, testBatchId, dryRun)
    };
    return {
      status: "success",
      action: "delete_test_batch",
      dry_run: dryRun,
      test_batch_id: testBatchId,
      sheets: results
    };
  } finally {
    lock.releaseLock();
  }
}

function deleteRowsInSheetByTestBatch_(sheet, testBatchId, dryRun) {
  const rows = getSheetRowsWithRowNumber_(sheet);
  const matchingRows = rows.filter(function(item) {
    return rowMatchesTestBatch_(item, testBatchId);
  });

  if (!dryRun) {
    for (var i = matchingRows.length - 1; i >= 0; i--) {
      sheet.deleteRow(matchingRows[i]._rowNumber);
    }
  }

  return {
    matched_rows: matchingRows.length,
    deleted_rows: dryRun ? 0 : matchingRows.length
  };
}

function getSheetRows_(sheet) {
  return getSheetRowsWithRowNumber_(sheet).map(function(item) {
    const clone = Object.assign({}, item);
    delete clone._rowNumber;
    return clone;
  });
}

function getSheetRowsWithRowNumber_(sheet) {
  const lastRow = sheet.getLastRow();
  const lastColumn = sheet.getLastColumn();
  if (lastRow < 2 || lastColumn === 0) {
    return [];
  }
  const headers = sheet.getRange(1, 1, 1, lastColumn).getValues()[0];
  const values = sheet.getRange(2, 1, lastRow - 1, lastColumn).getValues();
  return values.map(function(rowValues, rowIndex) {
    const row = { _rowNumber: rowIndex + 2 };
    headers.forEach(function(header, columnIndex) {
      row[String(header || "").trim()] = rowValues[columnIndex];
    });
    return row;
  });
}

function rowMatchesTestBatch_(row, testBatchId) {
  return normalizeBoolean_(row.is_test_data, false) && String(row.test_batch_id || "").trim() === testBatchId;
}

function normalizeBoolean_(value, defaultValue) {
  if (value === true || value === false) {
    return value;
  }
  if (value === null || value === undefined || value === "") {
    return defaultValue;
  }
  const normalized = String(value).trim().toLowerCase();
  if (normalized === "true" || normalized === "1" || normalized === "si" || normalized === "sí") {
    return true;
  }
  if (normalized === "false" || normalized === "0" || normalized === "no") {
    return false;
  }
  return defaultValue;
}

function upsertByKey_(sheet, keyColumns, payload, orderedColumns) {
  const lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    ensureHeader_(sheet, orderedColumns);
    const indexMap = getIndexMap_(sheet, keyColumns, orderedColumns);
    const key = buildCompositeKey_(payload, keyColumns);
    const row = orderedColumns.map(function(column) {
      const value = payload[column];
      return value === undefined || value === null ? "" : value;
    });

    if (indexMap[key]) {
      sheet.getRange(indexMap[key], 1, 1, orderedColumns.length).setValues([row]);
      return { mode: "update", rowNumber: indexMap[key] };
    }

    sheet.appendRow(row);
    return { mode: "insert", rowNumber: sheet.getLastRow() };
  } finally {
    lock.releaseLock();
  }
}

function ensureHeader_(sheet, columns) {
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(columns);
    return;
  }
  const existing = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  const needsUpdate = columns.some(function(column, index) {
    return existing[index] !== column;
  });
  if (needsUpdate) {
    sheet.getRange(1, 1, 1, columns.length).setValues([columns]);
  }
}

function getIndexMap_(sheet, keyColumns, orderedColumns) {
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) {
    return {};
  }
  const values = sheet.getRange(2, 1, lastRow - 1, orderedColumns.length).getValues();
  const keyIndexes = keyColumns.map(function(column) { return orderedColumns.indexOf(column); });
  const map = {};
  for (var i = 0; i < values.length; i++) {
    const key = keyIndexes.map(function(index) { return String(values[i][index] || "").trim(); }).join("||");
    if (key) {
      map[key] = i + 2;
    }
  }
  return map;
}

function buildCompositeKey_(payload, keyColumns) {
  return keyColumns.map(function(column) {
    return String(payload[column] || "").trim();
  }).join("||");
}

function isoNow_() {
  return new Date().toISOString();
}

function isoDateNow_() {
  return Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "yyyy-MM-dd");
}

function jsonResponse_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
