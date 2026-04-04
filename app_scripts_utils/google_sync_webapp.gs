function doPost(e) {
  try {
    const CONFIG = {
      token: "bankify_monitorias_2026_sync_9c7f1a42",
      spreadsheetId: "1ufR3nbA4jnxWaed2JUazdhduMCIM_PvWtwAJnexp4V4",
      writeSheets: {
        sesiones: "sesiones",
        respuestas: "respuestas",
        historialComentarios: "historial_comentarios",
        commentEvents: "comment_events",
        feedback: "feedback",
        control: "control_ingreso",
        legacyArchive: "legacy_row_archive",
        embeddingsCache: "embeddings_cache",
        projectionCache: "projection_cache"
      },
      exportableSheets: {
        sesiones: "sesiones",
        respuestas: "respuestas",
        historial_comentarios: "historial_comentarios",
        comment_events: "comment_events",
        feedback: "feedback",
        control_ingreso: "control_ingreso",
        embeddings_cache: "embeddings_cache",
        projection_cache: "projection_cache"
      }
    };

    const data = parseBody_(e);
    if (String(data.token || "") !== CONFIG.token) {
      return jsonResponse_({ status: "error", message: "No autorizado" });
    }

    const ss = SpreadsheetApp.openById(CONFIG.spreadsheetId);
    const sheets = ensureSheets_(ss, CONFIG.writeSheets);
    const action = String(data.accion || "").toLowerCase();

    if (action === "export_sheet_snapshot") {
      const result = exportSheetSnapshot_(ss, CONFIG.exportableSheets, data);
      return jsonResponse_(result);
    }

    if (action === "fix_legacy_rows") {
      return jsonResponse_(fixLegacyRows_(sheets, data));
    }

    if (action === "normalize_feedback_schema") {
      return jsonResponse_(normalizeFeedbackSchema_(sheets, data));
    }

    if (action === "archive_legacy_rows") {
      return jsonResponse_(archiveLegacyRows_(sheets, data));
    }

    if (action === "clear_sheet_rows") {
      return jsonResponse_(clearSheetRows_(sheets, data));
    }

    if (action === "backfill_embeddings_cache") {
      return jsonResponse_(backfillEmbeddingsCache_(sheets, data));
    }

    if (action === "query_projection_comments") {
      return jsonResponse_(queryProjectionComments_(sheets, data));
    }

    if (action === "query_comment_events") {
      return jsonResponse_(queryCommentEvents_(sheets, data, action));
    }

    if (action === "upsert_comment_events") {
      return jsonResponse_(upsertCommentEvents_(sheets, data));
    }

    if (action === "query_embeddings_cache") {
      return jsonResponse_(queryEmbeddingsCache_(sheets, data));
    }

    if (action === "upsert_embeddings_cache") {
      return jsonResponse_(upsertEmbeddingsCache_(sheets, data));
    }

    if (action === "query_projection_cache") {
      return jsonResponse_(queryProjectionCache_(sheets, data));
    }

    if (action === "upsert_projection_cache") {
      return jsonResponse_(upsertProjectionCache_(sheets, data));
    }

    if (action === "rebuild_projection_cache") {
      return jsonResponse_(rebuildProjectionCache_(sheets, data));
    }

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
          "access_code_display",
          "access_code_hash",
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

    if (action === "seed_test_batch") {
      const result = seedTestBatch_(sheets, data);
      return jsonResponse_(result);
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
        comment_events: getRowsByTestBatch_(sheets.commentEvents, testBatchId, exercise),
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

function exportSheetSnapshot_(ss, exportableSheets, data) {
  const requestedSheetNames = normalizeRequestedSheetNames_(data);
  const limitRows = normalizePositiveInteger_(data.limit_rows, 200, 500);
  const sheetSnapshots = {};

  requestedSheetNames.forEach(function(sheetName) {
    const resolvedSheetName = exportableSheets[sheetName];
    if (!resolvedSheetName) {
      throw new Error("Hoja no permitida para export_sheet_snapshot: " + sheetName);
    }
    const sheet = ss.getSheetByName(resolvedSheetName);
    if (!sheet) {
      throw new Error("La hoja solicitada no existe en el spreadsheet: " + resolvedSheetName);
    }
    sheetSnapshots[sheetName] = buildSheetSnapshot_(sheet, limitRows);
  });

  return {
    status: "success",
    action: "export_sheet_snapshot",
    requested_sheets: requestedSheetNames,
    limit_rows: limitRows,
    sheets: sheetSnapshots
  };
}

function normalizeRequestedSheetNames_(data) {
  const rawSheetNames = [];
  if (Array.isArray(data.sheet_names)) {
    rawSheetNames.push.apply(rawSheetNames, data.sheet_names);
  }
  if (Array.isArray(data.sheets)) {
    rawSheetNames.push.apply(rawSheetNames, data.sheets);
  }
  if (rawSheetNames.length === 0 && data.sheet_name) {
    rawSheetNames.push(data.sheet_name);
  }

  const normalized = [];
  const seen = {};
  rawSheetNames.forEach(function(value) {
    const name = String(value || "").trim();
    if (!name || seen[name]) {
      return;
    }
    normalized.push(name);
    seen[name] = true;
  });

  if (normalized.length === 0) {
    throw new Error("export_sheet_snapshot requiere al menos una hoja en sheet_names.");
  }
  return normalized;
}

function normalizePositiveInteger_(value, defaultValue, maxValue) {
  const numericValue = Number(value || defaultValue);
  if (isNaN(numericValue) || numericValue <= 0) {
    throw new Error("Se esperaba un entero positivo para limit_rows.");
  }
  return Math.min(Math.floor(numericValue), maxValue);
}

function buildSheetSnapshot_(sheet, limitRows) {
  const lastRow = sheet.getLastRow();
  const lastColumn = sheet.getLastColumn();
  const columns = getSheetHeaders_(sheet);
  const rows = getSheetRowsWithSnapshotMetadata_(sheet);
  const limitedRows = rows.slice(0, limitRows);

  return {
    sheet_name: sheet.getName(),
    column_count: lastColumn,
    columns: columns,
    total_rows: Math.max(lastRow - 1, 0),
    returned_rows: limitedRows.length,
    truncated: rows.length > limitedRows.length,
    rows: limitedRows
  };
}

function getSheetRowsWithSnapshotMetadata_(sheet) {
  return getSheetRowsWithRowNumber_(sheet).map(function(item) {
    const clone = Object.assign({}, item);
    clone._sheet_row_number = item._rowNumber;
    delete clone._rowNumber;
    return clone;
  });
}

function getSheetHeaders_(sheet) {
  const lastColumn = sheet.getLastColumn();
  if (lastColumn === 0) {
    return [];
  }
  return sheet.getRange(1, 1, 1, lastColumn).getValues()[0].map(function(header) {
    return String(header || "").trim();
  });
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
    access_code_display: String(
      data.access_code_display || profile.access_code_display || ""
    ).trim(),
    access_code_hash: String(data.access_code_hash || profile.access_code_hash || "").trim(),
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
  const historyPayload = buildCommentHistoryPayload_(payload);
  if (!historyPayload) {
    return;
  }

  upsertByKey_(
    sheet,
    ["participant_id", "exercise"],
    historyPayload,
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
      "captured_at"
    ]
  );
}

function buildCommentHistoryPayload_(payload) {
  const hasComments = [
    payload.dataset_comment,
    payload.analytics_comment,
    payload.prediction_reflection
  ].some(function(value) {
    return String(value || "").trim() !== "";
  });

  if (!hasComments) {
    return null;
  }

  return {
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
  };
}

function normalizeCommentEventRows_(rows) {
  if (!Array.isArray(rows) || rows.length === 0) {
    throw new Error("upsert_comment_events requiere rows no vacías.");
  }
  return rows.map(function(row) {
    const participantId = String(row.participant_id || "").trim();
    const exercise = String(row.exercise || "").trim();
    const commentType = String(row.comment_type || "").trim();
    const commentText = String(row.comment_text || row.comment || "").trim();
    const cleanComment = String(row.clean_comment || cleanCommentText_(commentText)).trim();
    const commentHash = String(row.comment_hash || buildCommentHash_(cleanComment, true)).trim();
    validateRequired_(
      {
        participant_id: participantId,
        exercise: exercise,
        comment_type: commentType,
        comment_text: commentText,
        comment_hash: commentHash
      },
      ["participant_id", "exercise", "comment_type", "comment_text", "comment_hash"]
    );
    return {
      participant_id: participantId,
      public_alias: String(row.public_alias || participantId).trim(),
      exercise: exercise,
      comment_type: commentType,
      comment_text: commentText,
      clean_comment: cleanComment,
      comment_hash: commentHash,
      updated_at: String(row.updated_at || isoNow_()).trim(),
      source_sheet_row_number: Number(row.source_sheet_row_number || 0),
      is_test_data: normalizeBoolean_(row.is_test_data, false),
      test_batch_id: String(row.test_batch_id || "").trim(),
      data_origin: String(row.data_origin || "app_runtime").trim()
    };
  });
}

function queryCommentEvents_(sheets, data, action) {
  const exercise = String(data.exercise || "").trim();
  validateRequired_({ exercise: exercise }, ["exercise"]);
  const limitRows = normalizePositiveInteger_(data.limit_rows, 500, 5000);
  const rows = getSheetRowsWithRowNumber_(sheets.commentEvents)
    .filter(function(row) {
      return String(row.exercise || "").trim() === exercise;
    })
    .filter(function(row) {
      return String(row.comment_text || "").trim() !== "";
    })
    .slice(0, limitRows)
    .map(function(row) {
      return {
        participant_id: String(row.participant_id || "").trim(),
        public_alias: String(row.public_alias || row.participant_id || "").trim(),
        exercise: String(row.exercise || "").trim(),
        comment_type: String(row.comment_type || "").trim(),
        comment_text: String(row.comment_text || row.comment || "").trim(),
        clean_comment: String(row.clean_comment || "").trim(),
        comment_hash: String(row.comment_hash || "").trim(),
        updated_at: String(row.updated_at || "").trim(),
        source_sheet_row_number: row._rowNumber,
        is_test_data: normalizeBoolean_(row.is_test_data, false),
        test_batch_id: String(row.test_batch_id || "").trim(),
        data_origin: String(row.data_origin || "app_runtime").trim()
      };
    });

  return {
    status: "success",
    action: action || "query_comment_events",
    exercise: exercise,
    rows: rows,
    returned_rows: rows.length
  };
}

function upsertCommentEvents_(sheets, data) {
  const rows = normalizeCommentEventRows_(data.rows);
  const writeResult = upsertManyByKey_(
    sheets.commentEvents,
    ["participant_id", "exercise", "comment_type"],
    rows,
    [
      "participant_id",
      "public_alias",
      "exercise",
      "comment_type",
      "comment_text",
      "clean_comment",
      "comment_hash",
      "updated_at",
      "source_sheet_row_number",
      "is_test_data",
      "test_batch_id",
      "data_origin"
    ]
  );
  SpreadsheetApp.flush();
  return {
    status: "success",
    action: "upsert_comment_events",
    write_result: writeResult,
    rows: rows.length
  };
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

function seedTestBatch_(sheets, data) {
  const records = normalizeSeedBatchRecords_(data);
  if (records.length === 0) {
    throw new Error("seed_test_batch requiere al menos un registro.");
  }

  const lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    const sessionPayloads = [];
    const sessionControlPayloads = [];
    const progressPayloads = [];
    const historyPayloads = [];
    const commentEventPayloads = [];
    const feedbackPayloads = [];
    const completedPayloads = [];

    records.forEach(function(record) {
      sessionPayloads.push(record.session);
      sessionControlPayloads.push({
        participant_id: record.session.participant_id,
        exercise: "session",
        status: "active",
        is_test_data: record.session.is_test_data,
        test_batch_id: record.session.test_batch_id,
        data_origin: record.session.data_origin,
        updated_at: record.session.updated_at
      });
      progressPayloads.push(record.progress);
      if (record.history) {
        historyPayloads.push(record.history);
      }
      if (record.commentEvents && record.commentEvents.length > 0) {
        Array.prototype.push.apply(commentEventPayloads, record.commentEvents);
      }
      feedbackPayloads.push(record.feedback);
      completedPayloads.push(record.completed);
    });

    return {
      status: "success",
      action: "seed_test_batch",
      test_batch_id: String(data.test_batch_id || records[0].session.test_batch_id || "").trim(),
      chunk_index: Number(data.chunk_index || 1),
      total_chunks: Number(data.total_chunks || 1),
      processed_records: records.length,
      sheets: {
        sesiones: upsertManyByKey_(
          sheets.sesiones,
          ["participant_id"],
          sessionPayloads,
          [
            "participant_id",
            "public_alias",
            "access_code_display",
            "access_code_hash",
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
        ),
        control_session: upsertManyByKey_(
          sheets.control,
          ["participant_id", "exercise"],
          sessionControlPayloads,
          ["participant_id", "exercise", "status", "is_test_data", "test_batch_id", "data_origin", "updated_at"]
        ),
        respuestas: upsertManyByKey_(
          sheets.respuestas,
          ["participant_id", "exercise"],
          progressPayloads,
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
        ),
        historial_comentarios: upsertManyByKey_(
          sheets.historialComentarios,
          ["participant_id", "exercise"],
          historyPayloads,
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
            "captured_at"
          ]
        ),
        comment_events: upsertManyByKey_(
          sheets.commentEvents,
          ["participant_id", "exercise", "comment_type"],
          commentEventPayloads,
          [
            "participant_id",
            "public_alias",
            "exercise",
            "comment_type",
            "comment_text",
            "clean_comment",
            "comment_hash",
            "updated_at",
            "source_sheet_row_number",
            "is_test_data",
            "test_batch_id",
            "data_origin"
          ]
        ),
        feedback: upsertManyByKey_(
          sheets.feedback,
          ["participant_id", "exercise"],
          feedbackPayloads,
          ["participant_id", "exercise", "rating", "summary", "missing_topics", "improvement_ideas", "is_test_data", "test_batch_id", "data_origin", "updated_at"]
        ),
        control_completed: upsertManyByKey_(
          sheets.control,
          ["participant_id", "exercise"],
          completedPayloads,
          ["participant_id", "exercise", "status", "is_test_data", "test_batch_id", "data_origin", "updated_at"]
        )
      }
    };
  } finally {
    lock.releaseLock();
  }
}

function normalizeSeedBatchRecords_(data) {
  const records = Array.isArray(data.records) ? data.records : [];
  return records.map(function(record) {
    const traceabilitySource = Object.assign({}, record.traceability_payload || {}, {
      test_batch_id: record.test_batch_id || (record.traceability_payload || {}).test_batch_id || data.test_batch_id || "",
      is_test_data: record.is_test_data,
      data_origin: record.data_origin || (record.traceability_payload || {}).data_origin || data.data_origin || ""
    });

    const session = normalizeSessionPayload_(Object.assign({}, traceabilitySource, {
      participant_id: record.participant_id,
      public_alias: record.public_alias,
      profile: record.profile || {}
    }));
    validateRequired_(session, ["participant_id", "public_alias"]);

    const progress = normalizeProgressPayload_(Object.assign({}, traceabilitySource, {
      participant_id: record.participant_id,
      exercise: record.exercise,
      payload: record.progress_payload || {}
    }));
    validateRequired_(progress, ["participant_id", "exercise"]);

    const feedback = normalizeFeedbackPayload_(Object.assign({}, traceabilitySource, {
      participant_id: record.participant_id,
      exercise: record.exercise,
      payload: record.feedback_payload || {}
    }));
    validateRequired_(feedback, ["participant_id", "exercise"]);
    const commentEvents = buildCommentEventRowsFromSeedRecord_(record, progress, session.public_alias);

    return {
      session: session,
      progress: progress,
      history: buildCommentHistoryPayload_(progress),
      commentEvents: commentEvents,
      feedback: feedback,
      completed: {
        participant_id: progress.participant_id,
        exercise: progress.exercise,
        status: "completed",
        is_test_data: progress.is_test_data,
        test_batch_id: progress.test_batch_id,
        data_origin: progress.data_origin,
        updated_at: isoNow_()
      }
    };
  });
}

function buildCommentEventRowsFromSeedRecord_(record, progress, publicAlias) {
  const providedRows = Array.isArray(record.comment_events) ? record.comment_events : [];
  if (providedRows.length > 0) {
    return normalizeCommentEventRows_(providedRows);
  }

  const commentTypes = ["dataset_comment", "analytics_comment", "prediction_reflection"];
  return commentTypes.map(function(commentType) {
    const commentText = String(progress[commentType] || "").trim();
    if (!commentText) {
      return null;
    }
    return {
      participant_id: progress.participant_id,
      public_alias: String(publicAlias || progress.participant_id).trim() || progress.participant_id,
      exercise: progress.exercise,
      comment_type: commentType,
      comment_text: commentText,
      clean_comment: cleanCommentText_(commentText),
      comment_hash: buildCommentHash_(commentText, false),
      updated_at: progress.updated_at,
      source_sheet_row_number: 0,
      is_test_data: progress.is_test_data,
      test_batch_id: progress.test_batch_id,
      data_origin: progress.data_origin
    };
  }).filter(function(row) {
    return row !== null;
  });
}

const COMMENT_EVENT_STOPWORDS_ = {
  de: true, la: true, el: true, los: true, las: true, que: true, y: true, o: true,
  en: true, un: true, una: true, para: true, por: true, con: true, del: true,
  al: true, se: true, su: true, sus: true, me: true, mi: true, mis: true,
  es: true, son: true, muy: true, mas: true, pero: true, porque: true,
  como: true, lo: true, le: true, les: true, ha: true, han: true, fue: true,
  ser: true, estar: true
};

function cleanCommentText_(text) {
  const normalized = String(text || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/https?:\/\/\S+|www\.\S+/g, " ")
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  return normalized.split(" ").filter(function(token) {
    return token && !COMMENT_EVENT_STOPWORDS_[token];
  }).join(" ");
}

function buildCommentHash_(comment, isClean) {
  const normalized = isClean ? String(comment || "").trim() : cleanCommentText_(comment);
  const digest = Utilities.computeDigest(
    Utilities.DigestAlgorithm.SHA_256,
    normalized,
    Utilities.Charset.UTF_8
  );
  return digest.map(function(byteValue) {
    const normalizedByte = byteValue < 0 ? byteValue + 256 : byteValue;
    const hex = normalizedByte.toString(16);
    return hex.length === 1 ? "0" + hex : hex;
  }).join("");
}

function fixLegacyRows_(sheets, data) {
  const sourceSheet = getAdminSheetByName_(sheets, String(data.source_sheet || "respuestas").trim());
  const dryRun = normalizeBoolean_(data.dry_run, true);
  const lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    const matchingRows = getMatchingRowsForAdminAction_(sourceSheet, data.legacy_row_selectors, {
      onlyLegacy: true,
      exercise: String(data.exercise || "").trim()
    });
    const plannedUpdates = matchingRows.map(function(row) {
      return buildFixedLegacyRow_(row);
    }).filter(function(item) {
      return item.has_changes;
    });

    if (!dryRun && plannedUpdates.length > 0) {
      updateSheetRowsByRowNumber_(sourceSheet, plannedUpdates, [
        "participant_id",
        "exercise",
        "dataset_comment",
        "analytics_comment",
        "prediction_reflection",
        "updated_at",
        "data_origin"
      ]);
      SpreadsheetApp.flush();
    }

    return {
      status: "success",
      action: "fix_legacy_rows",
      dry_run: dryRun,
      source_sheet: sourceSheet.getName(),
      matched_rows: matchingRows.length,
      changed_rows: plannedUpdates.length,
      rows: plannedUpdates.map(function(item) {
        return {
          row_number: item._rowNumber,
          participant_id: String(item.participant_id || "").trim(),
          exercise: String(item.exercise || "").trim(),
          applied_fields: item._appliedFields
        };
      })
    };
  } finally {
    lock.releaseLock();
  }
}

function normalizeFeedbackSchema_(sheets, data) {
  const sourceSheet = getAdminSheetByName_(sheets, String(data.source_sheet || "respuestas").trim());
  const dryRun = normalizeBoolean_(data.dry_run, true);
  const exercise = String(data.exercise || "").trim();
  const matchingRows = getMatchingRowsForAdminAction_(sourceSheet, data.legacy_row_selectors, {
    onlyLegacy: false,
    exercise: exercise
  });
  const feedbackPayloads = matchingRows.map(function(row) {
    return buildFeedbackPayloadFromLegacyRow_(row);
  }).filter(function(item) {
    return item !== null;
  });

  let writeResult = { inserted: 0, updated: 0, total: feedbackPayloads.length };
  if (!dryRun && feedbackPayloads.length > 0) {
    writeResult = upsertManyByKey_(
      sheets.feedback,
      ["participant_id", "exercise"],
      feedbackPayloads,
      [
        "participant_id",
        "exercise",
        "rating",
        "summary",
        "missing_topics",
        "improvement_ideas",
        "is_test_data",
        "test_batch_id",
        "data_origin",
        "updated_at"
      ]
    );
  }

  return {
    status: "success",
    action: "normalize_feedback_schema",
    dry_run: dryRun,
    source_sheet: sourceSheet.getName(),
    matched_rows: matchingRows.length,
    normalized_feedback_rows: feedbackPayloads.length,
    write_result: writeResult,
    preview: feedbackPayloads.slice(0, 20)
  };
}

function archiveLegacyRows_(sheets, data) {
  const sourceSheet = getAdminSheetByName_(sheets, String(data.source_sheet || "respuestas").trim());
  const dryRun = normalizeBoolean_(data.dry_run, true);
  const archiveReason = String(data.archive_reason || "legacy_snapshot_cleanup").trim();
  requireAdminConfirmation_("archive_legacy_rows", dryRun, String(data.confirm_phrase || "").trim());

  const lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    const matchingRows = getMatchingRowsForAdminAction_(sourceSheet, data.legacy_row_selectors, {
      onlyLegacy: true,
      exercise: String(data.exercise || "").trim()
    });
    const archiveRows = matchingRows.map(function(row) {
      return buildLegacyArchivePayload_(sourceSheet.getName(), row, archiveReason);
    });
    const deletionBlocks = buildDescendingRowDeletionBlocks_(matchingRows.map(function(row) {
      return row._rowNumber;
    }));

    if (!dryRun && archiveRows.length > 0) {
      appendObjectsToSheet_(sheets.legacyArchive, archiveRows, [
        "archive_batch_id",
        "archived_at",
        "archive_reason",
        "source_sheet",
        "source_row_number",
        "participant_id",
        "exercise",
        "test_batch_id",
        "data_origin",
        "row_json"
      ]);
      deletionBlocks.forEach(function(block) {
        sourceSheet.deleteRows(block.start_row, block.row_count);
      });
      SpreadsheetApp.flush();
    }

    return {
      status: "success",
      action: "archive_legacy_rows",
      dry_run: dryRun,
      source_sheet: sourceSheet.getName(),
      archive_reason: archiveReason,
      matched_rows: matchingRows.length,
      archived_rows: dryRun ? 0 : archiveRows.length,
      deleted_blocks: dryRun ? 0 : deletionBlocks.length,
      preview: archiveRows.slice(0, 20)
    };
  } finally {
    lock.releaseLock();
  }
}

function clearSheetRows_(sheets, data) {
  const targetSheet = getAdminSheetByName_(sheets, String(data.target_sheet || "").trim());
  const dryRun = normalizeBoolean_(data.dry_run, true);
  requireAdminConfirmation_("clear_sheet_rows", dryRun, String(data.confirm_phrase || "").trim());
  const rowFilters = data.row_filters || {};
  const rows = getSheetRowsWithRowNumber_(targetSheet);
  const matchingRowNumbers = rows.filter(function(row) {
    return rowMatchesAdminFilters_(row, rowFilters);
  }).map(function(row) {
    return row._rowNumber;
  });
  const deletionBlocks = buildDescendingRowDeletionBlocks_(matchingRowNumbers);

  if (!dryRun) {
    deletionBlocks.forEach(function(block) {
      targetSheet.deleteRows(block.start_row, block.row_count);
    });
    SpreadsheetApp.flush();
  }

  return {
    status: "success",
    action: "clear_sheet_rows",
    dry_run: dryRun,
    target_sheet: targetSheet.getName(),
    matched_rows: matchingRowNumbers.length,
    deleted_rows: dryRun ? 0 : matchingRowNumbers.length,
    deleted_blocks: dryRun ? 0 : deletionBlocks.length,
    row_filters: rowFilters
  };
}

function backfillEmbeddingsCache_(sheets, data) {
  const dryRun = normalizeBoolean_(data.dry_run, true);
  const rows = normalizeEmbeddingsCacheRows_(data.rows);
  let writeResult = { inserted: 0, updated: 0, total: rows.length };
  if (!dryRun && rows.length > 0) {
    writeResult = upsertManyByKey_(
      sheets.embeddingsCache,
      ["exercise", "comment_hash", "embedding_version"],
      rows,
      [
        "participant_id",
        "exercise",
        "comment_hash",
        "embedding_version",
        "embedding_provider",
        "comment_text",
        "clean_comment",
        "embedding_vector_json",
        "source_updated_at",
        "source_sheet_row_number",
        "cache_key",
        "updated_at"
      ]
    );
  }

  return {
    status: "success",
    action: "backfill_embeddings_cache",
    dry_run: dryRun,
    processed_rows: rows.length,
    write_result: writeResult,
    preview: rows.slice(0, 20)
  };
}

function queryProjectionComments_(sheets, data) {
  const exercise = String(data.exercise || "").trim();
  validateRequired_({ exercise: exercise }, ["exercise"]);
  const limitRows = normalizePositiveInteger_(data.limit_rows, 500, 5000);
  const aliasesByParticipant = {};
  getSheetRows_(sheets.sesiones).forEach(function(row) {
    const participantId = String(row.participant_id || "").trim();
    if (!participantId) {
      return;
    }
    aliasesByParticipant[participantId] = String(row.public_alias || participantId).trim() || participantId;
  });

  const rows = getSheetRowsWithRowNumber_(sheets.respuestas)
    .filter(function(row) {
      return String(row.exercise || "").trim() === exercise;
    })
    .filter(function(row) {
      return hasProjectionCommentData_(row);
    })
    .slice(0, limitRows)
    .map(function(row) {
      const participantId = String(row.participant_id || "").trim();
      return {
        participant_id: participantId,
        public_alias: aliasesByParticipant[participantId] || participantId,
        exercise: exercise,
        dataset_comment: String(row.dataset_comment || "").trim(),
        analytics_comment: String(row.analytics_comment || "").trim(),
        prediction_reflection: String(row.prediction_reflection || "").trim(),
        combined_comment: buildCombinedProjectionComment_(row),
        prediction_output: String(row.prediction_output || "").trim(),
        updated_at: String(row.updated_at || "").trim(),
        source_sheet_row_number: row._rowNumber
      };
    });

  return {
    status: "success",
    action: "query_projection_comments",
    exercise: exercise,
    rows: rows,
    returned_rows: rows.length
  };
}

function queryEmbeddingsCache_(sheets, data) {
  const exercise = String(data.exercise || "").trim();
  const embeddingVersion = String(data.embedding_version || "").trim();
  validateRequired_({ exercise: exercise, embedding_version: embeddingVersion }, ["exercise", "embedding_version"]);
  const filters = normalizeCacheQueryFilters_(data);
  const rows = getSheetRows_(sheets.embeddingsCache).filter(function(row) {
    return rowMatchesCacheQuery_(row, filters, embeddingVersion, "");
  });
  return {
    status: "success",
    action: "query_embeddings_cache",
    exercise: exercise,
    embedding_version: embeddingVersion,
    rows: rows
  };
}

function upsertEmbeddingsCache_(sheets, data) {
  const rows = normalizeEmbeddingsCacheRows_(data.rows);
  const writeResult = upsertManyByKey_(
    sheets.embeddingsCache,
    ["exercise", "comment_hash", "embedding_version"],
    rows,
    [
      "participant_id",
      "exercise",
      "comment_hash",
      "embedding_version",
      "embedding_provider",
      "comment_text",
      "clean_comment",
      "embedding_vector_json",
      "source_updated_at",
      "source_sheet_row_number",
      "cache_key",
      "updated_at"
    ]
  );
  SpreadsheetApp.flush();
  return {
    status: "success",
    action: "upsert_embeddings_cache",
    write_result: writeResult,
    rows: rows.length
  };
}

function queryProjectionCache_(sheets, data) {
  const exercise = String(data.exercise || "").trim();
  const projectionVersion = String(data.projection_version || "").trim();
  validateRequired_({ exercise: exercise, projection_version: projectionVersion }, ["exercise", "projection_version"]);
  const filters = normalizeCacheQueryFilters_(data);
  const rows = getSheetRows_(sheets.projectionCache).filter(function(row) {
    return rowMatchesCacheQuery_(row, filters, "", projectionVersion);
  });
  return {
    status: "success",
    action: "query_projection_cache",
    exercise: exercise,
    projection_version: projectionVersion,
    rows: rows
  };
}

function upsertProjectionCache_(sheets, data) {
  const rows = normalizeProjectionCacheRows_(data.rows, "", "");
  const writeResult = upsertManyByKey_(
    sheets.projectionCache,
    ["exercise", "comment_hash", "projection_version"],
    rows,
    [
      "participant_id",
      "exercise",
      "comment_hash",
      "projection_version",
      "embedding_provider",
      "reduction_provider",
      "public_alias",
      "comment_text",
      "clean_comment",
      "x",
      "y",
      "z",
      "source_updated_at",
      "source_sheet_row_number",
      "updated_at"
    ]
  );
  SpreadsheetApp.flush();
  return {
    status: "success",
    action: "upsert_projection_cache",
    write_result: writeResult,
    rows: rows.length
  };
}

function rebuildProjectionCache_(sheets, data) {
  const dryRun = normalizeBoolean_(data.dry_run, true);
  const replaceExistingScope = normalizeBoolean_(data.replace_existing_scope, true);
  const exercise = String(data.exercise || "").trim();
  const projectionVersion = String(data.projection_version || "").trim();
  validateRequired_({ exercise: exercise, projection_version: projectionVersion }, ["exercise", "projection_version"]);
  requireAdminConfirmation_(
    "rebuild_projection_cache",
    dryRun,
    String(data.confirm_phrase || "").trim(),
    replaceExistingScope
  );

  const rows = normalizeProjectionCacheRows_(data.rows, exercise, projectionVersion);
  const rowFilters = {
    exercise: exercise,
    projection_version: projectionVersion,
    only_legacy: false
  };
  const existingRows = getSheetRowsWithRowNumber_(sheets.projectionCache).filter(function(row) {
    return rowMatchesAdminFilters_(row, rowFilters);
  });
  const deletionBlocks = buildDescendingRowDeletionBlocks_(existingRows.map(function(row) {
    return row._rowNumber;
  }));

  let writeResult = { inserted: 0, updated: 0, total: rows.length };
  if (!dryRun) {
    if (replaceExistingScope) {
      deletionBlocks.forEach(function(block) {
        sheets.projectionCache.deleteRows(block.start_row, block.row_count);
      });
      appendObjectsToSheet_(sheets.projectionCache, rows, [
        "participant_id",
        "exercise",
        "comment_hash",
        "projection_version",
        "embedding_provider",
        "reduction_provider",
        "public_alias",
        "comment_text",
        "clean_comment",
        "x",
        "y",
        "z",
        "source_updated_at",
        "source_sheet_row_number",
        "updated_at"
      ]);
      writeResult = { inserted: rows.length, updated: 0, total: rows.length };
    } else if (rows.length > 0) {
      writeResult = upsertManyByKey_(
        sheets.projectionCache,
        ["exercise", "comment_hash", "projection_version"],
        rows,
        [
          "participant_id",
          "exercise",
          "comment_hash",
          "projection_version",
          "embedding_provider",
          "reduction_provider",
          "public_alias",
          "comment_text",
          "clean_comment",
          "x",
          "y",
          "z",
          "source_updated_at",
          "source_sheet_row_number",
          "updated_at"
        ]
      );
    }
    SpreadsheetApp.flush();
  }

  return {
    status: "success",
    action: "rebuild_projection_cache",
    dry_run: dryRun,
    replace_existing_scope: replaceExistingScope,
    exercise: exercise,
    projection_version: projectionVersion,
    existing_scope_rows: existingRows.length,
    removed_scope_rows: dryRun || !replaceExistingScope ? 0 : existingRows.length,
    write_result: writeResult,
    preview: rows.slice(0, 20)
  };
}

function getAdminSheetByName_(sheets, requestedName) {
  const allowed = {
    sesiones: sheets.sesiones,
    respuestas: sheets.respuestas,
    historial_comentarios: sheets.historialComentarios,
    comment_events: sheets.commentEvents,
    feedback: sheets.feedback,
    control_ingreso: sheets.control,
    embeddings_cache: sheets.embeddingsCache,
    projection_cache: sheets.projectionCache,
    legacy_row_archive: sheets.legacyArchive
  };
  const sheet = allowed[requestedName];
  if (!sheet) {
    throw new Error("Hoja no permitida para acción administrativa: " + requestedName);
  }
  return sheet;
}

function requireAdminConfirmation_(action, dryRun, confirmPhrase, isRequired) {
  const required = isRequired === undefined ? true : isRequired;
  if (dryRun || !required) {
    return;
  }
  const expectedByAction = {
    archive_legacy_rows: "ARCHIVE_LEGACY_ROWS",
    clear_sheet_rows: "CLEAR_SHEET_ROWS",
    rebuild_projection_cache: "REBUILD_PROJECTION_CACHE"
  };
  const expected = expectedByAction[action];
  if (confirmPhrase !== expected) {
    throw new Error("Confirmación rechazada para " + action + ": confirm_phrase inválido.");
  }
}

function getMatchingRowsForAdminAction_(sheet, selectors, options) {
  const normalizedOptions = options || {};
  return getSheetRowsWithRowNumber_(sheet).filter(function(row) {
    if (normalizedOptions.onlyLegacy && !isLegacyRow_(row)) {
      return false;
    }
    if (normalizedOptions.exercise && String(row.exercise || row.ejercicio || "").trim() !== normalizedOptions.exercise) {
      return false;
    }
    if (!selectors || !selectors.length) {
      return true;
    }
    return selectors.some(function(selector) {
      return rowMatchesSelector_(row, selector);
    });
  });
}

function rowMatchesSelector_(row, selector) {
  const rowNumber = Number(selector.row_number || 0);
  if (rowNumber > 0 && row._rowNumber !== rowNumber) {
    return false;
  }
  if (selector.participant_id && String(row.participant_id || row.id || "").trim() !== String(selector.participant_id).trim()) {
    return false;
  }
  if (selector.exercise && String(row.exercise || row.ejercicio || "").trim() !== String(selector.exercise).trim()) {
    return false;
  }
  if (selector.test_batch_id && String(row.test_batch_id || "").trim() !== String(selector.test_batch_id).trim()) {
    return false;
  }
  if (selector.data_origin && String(row.data_origin || "").trim() !== String(selector.data_origin).trim()) {
    return false;
  }
  return true;
}

function isLegacyRow_(row) {
  return [
    row.id,
    row.ejercicio,
    row.comentario,
    row.que_parecio,
    row.que_hubiera_gustado,
    row.cosas_mejorar,
    row.feedback_rating,
    row.feedback_summary,
    row.feedback_missing_topics,
    row.feedback_improvement_ideas,
    row.selected_exercise,
    row.completed_at
  ].some(function(value) {
    return String(value || "").trim() !== "";
  });
}

function buildFixedLegacyRow_(row) {
  const updatedRow = Object.assign({}, row);
  updatedRow._appliedFields = [];
  if (!String(updatedRow.participant_id || "").trim() && String(updatedRow.id || "").trim()) {
    updatedRow.participant_id = String(updatedRow.id || "").trim();
    updatedRow._appliedFields.push("participant_id<=id");
  }
  if (!String(updatedRow.exercise || "").trim() && String(updatedRow.ejercicio || updatedRow.selected_exercise || "").trim()) {
    updatedRow.exercise = String(updatedRow.ejercicio || updatedRow.selected_exercise || "").trim();
    updatedRow._appliedFields.push("exercise<=ejercicio|selected_exercise");
  }
  if (!String(updatedRow.dataset_comment || "").trim() && String(updatedRow.comentario || "").trim()) {
    updatedRow.dataset_comment = String(updatedRow.comentario || "").trim();
    updatedRow._appliedFields.push("dataset_comment<=comentario");
  }
  if (!String(updatedRow.updated_at || "").trim()) {
    updatedRow.updated_at = isoNow_();
    updatedRow._appliedFields.push("updated_at<=isoNow");
  }
  if (!String(updatedRow.data_origin || "").trim()) {
    updatedRow.data_origin = "legacy_snapshot_repair";
    updatedRow._appliedFields.push("data_origin<=legacy_snapshot_repair");
  }
  updatedRow.has_changes = updatedRow._appliedFields.length > 0;
  return updatedRow;
}

function buildFeedbackPayloadFromLegacyRow_(row) {
  const participantId = String(row.participant_id || row.id || "").trim();
  const exercise = String(row.exercise || row.ejercicio || row.selected_exercise || "").trim();
  const rating = Number(row.rating || row.feedback_rating || row.calificacion || 0);
  const summary = String(row.summary || row.feedback_summary || row.que_parecio || "").trim();
  const missingTopics = String(
    row.missing_topics || row.feedback_missing_topics || row.que_hubiera_gustado || ""
  ).trim();
  const improvementIdeas = String(
    row.improvement_ideas || row.feedback_improvement_ideas || row.cosas_mejorar || ""
  ).trim();
  if (!participantId || !exercise) {
    return null;
  }
  if (!summary && !missingTopics && !improvementIdeas && rating === 0) {
    return null;
  }
  return {
    participant_id: participantId,
    exercise: exercise,
    rating: rating,
    summary: summary,
    missing_topics: missingTopics,
    improvement_ideas: improvementIdeas,
    is_test_data: normalizeBoolean_(row.is_test_data, false),
    test_batch_id: String(row.test_batch_id || "").trim(),
    data_origin: String(row.data_origin || "legacy_feedback_normalized").trim(),
    updated_at: isoNow_()
  };
}

function buildLegacyArchivePayload_(sourceSheetName, row, archiveReason) {
  return {
    archive_batch_id: Utilities.getUuid(),
    archived_at: isoNow_(),
    archive_reason: archiveReason,
    source_sheet: sourceSheetName,
    source_row_number: row._rowNumber,
    participant_id: String(row.participant_id || row.id || "").trim(),
    exercise: String(row.exercise || row.ejercicio || row.selected_exercise || "").trim(),
    test_batch_id: String(row.test_batch_id || "").trim(),
    data_origin: String(row.data_origin || "").trim(),
    row_json: JSON.stringify(stripRowNumber_(row))
  };
}

function rowMatchesAdminFilters_(row, filters) {
  const normalizedFilters = filters || {};
  const rowNumbers = Array.isArray(normalizedFilters.row_numbers) ? normalizedFilters.row_numbers : [];
  const participantIds = Array.isArray(normalizedFilters.participant_ids) ? normalizedFilters.participant_ids : [];
  if (rowNumbers.length > 0 && rowNumbers.indexOf(row._rowNumber) === -1) {
    return false;
  }
  if (participantIds.length > 0) {
    const participantId = String(row.participant_id || row.id || "").trim();
    if (participantIds.map(function(value) { return String(value).trim(); }).indexOf(participantId) === -1) {
      return false;
    }
  }
  if (normalizedFilters.exercise && String(row.exercise || row.ejercicio || "").trim() !== String(normalizedFilters.exercise).trim()) {
    return false;
  }
  if (normalizedFilters.test_batch_id && String(row.test_batch_id || "").trim() !== String(normalizedFilters.test_batch_id).trim()) {
    return false;
  }
  if (normalizedFilters.data_origin && String(row.data_origin || "").trim() !== String(normalizedFilters.data_origin).trim()) {
    return false;
  }
  if (normalizedFilters.projection_version && String(row.projection_version || "").trim() !== String(normalizedFilters.projection_version).trim()) {
    return false;
  }
  if (normalizedFilters.embedding_version && String(row.embedding_version || "").trim() !== String(normalizedFilters.embedding_version).trim()) {
    return false;
  }
  if (normalizeBoolean_(normalizedFilters.only_legacy, false) && !isLegacyRow_(row)) {
    return false;
  }
  return true;
}

function normalizeEmbeddingsCacheRows_(rows) {
  if (!Array.isArray(rows) || rows.length === 0) {
    throw new Error("backfill_embeddings_cache requiere rows no vacías.");
  }
  return rows.map(function(row) {
    const participantId = String(row.participant_id || "").trim();
    const exercise = String(row.exercise || "").trim();
    const commentHash = String(row.comment_hash || "").trim();
    const embeddingVersion = String(row.embedding_version || "").trim();
    validateRequired_(
      {
        participant_id: participantId,
        exercise: exercise,
        comment_hash: commentHash,
        embedding_version: embeddingVersion
      },
      ["participant_id", "exercise", "comment_hash", "embedding_version"]
    );
    return {
      participant_id: participantId,
      exercise: exercise,
      comment_hash: commentHash,
      embedding_version: embeddingVersion,
      embedding_provider: String(row.embedding_provider || "").trim(),
      comment_text: String(row.comment_text || row.comment || "").trim(),
      clean_comment: String(row.clean_comment || "").trim(),
      embedding_vector_json: normalizeJsonStringField_(row.embedding_vector_json || row.embedding_vector || []),
      source_updated_at: String(row.source_updated_at || "").trim(),
      source_sheet_row_number: Number(row.source_sheet_row_number || 0),
      cache_key: String(row.cache_key || [participantId, exercise, commentHash, embeddingVersion].join("::")).trim(),
      updated_at: isoNow_()
    };
  });
}

function normalizeProjectionCacheRows_(rows, exercise, projectionVersion) {
  if (!Array.isArray(rows) || rows.length === 0) {
    throw new Error("rebuild_projection_cache requiere rows no vacías.");
  }
  return rows.map(function(row) {
    const participantId = String(row.participant_id || "").trim();
    const commentHash = String(row.comment_hash || "").trim();
    validateRequired_({ participant_id: participantId, comment_hash: commentHash }, ["participant_id", "comment_hash"]);
    return {
      participant_id: participantId,
      exercise: String(row.exercise || exercise || "").trim(),
      comment_hash: commentHash,
      projection_version: String(row.projection_version || projectionVersion || "").trim(),
      embedding_provider: String(row.embedding_provider || "").trim(),
      reduction_provider: String(row.reduction_provider || "").trim(),
      public_alias: String(row.public_alias || participantId).trim(),
      comment_text: String(row.comment_text || row.comment || "").trim(),
      clean_comment: String(row.clean_comment || "").trim(),
      x: Number(row.x || 0),
      y: Number(row.y || 0),
      z: Number(row.z || 0),
      source_updated_at: String(row.source_updated_at || "").trim(),
      source_sheet_row_number: Number(row.source_sheet_row_number || 0),
      updated_at: isoNow_()
    };
  });
}

function normalizeJsonStringField_(value) {
  if (typeof value === "string") {
    return value;
  }
  return JSON.stringify(value || []);
}

function hasProjectionCommentData_(row) {
  return buildCombinedProjectionComment_(row) !== "" && String(row.prediction_output || "").trim() !== "" && String(row.prediction_output || "").trim() !== "{}";
}

function buildCombinedProjectionComment_(row) {
  return [row.dataset_comment, row.analytics_comment, row.prediction_reflection]
    .map(function(value) { return String(value || "").trim(); })
    .filter(function(value) { return value !== ""; })
    .join(" ")
    .trim();
}

function normalizeCacheQueryFilters_(data) {
  return {
    exercise: String(data.exercise || "").trim(),
    embedding_version: String(data.embedding_version || "").trim(),
    projection_version: String(data.projection_version || "").trim(),
    participant_ids: Array.isArray(data.participant_ids) ? data.participant_ids.map(function(value) { return String(value || "").trim(); }).filter(Boolean) : [],
    comment_hashes: Array.isArray(data.comment_hashes) ? data.comment_hashes.map(function(value) { return String(value || "").trim(); }).filter(Boolean) : []
  };
}

function rowMatchesCacheQuery_(row, filters, embeddingVersion, projectionVersion) {
  if (filters.exercise && String(row.exercise || "").trim() !== filters.exercise) {
    return false;
  }
  if (embeddingVersion && String(row.embedding_version || "").trim() !== embeddingVersion) {
    return false;
  }
  if (projectionVersion && String(row.projection_version || "").trim() !== projectionVersion) {
    return false;
  }
  if (filters.participant_ids.length > 0 && filters.participant_ids.indexOf(String(row.participant_id || "").trim()) === -1) {
    return false;
  }
  if (filters.comment_hashes.length > 0 && filters.comment_hashes.indexOf(String(row.comment_hash || "").trim()) === -1) {
    return false;
  }
  return true;
}

function stripRowNumber_(row) {
  const clone = Object.assign({}, row);
  delete clone._rowNumber;
  return clone;
}

function updateSheetRowsByRowNumber_(sheet, rows, requiredColumns) {
  if (!rows || rows.length === 0) {
    return;
  }
  const headers = ensureColumnsPresent_(sheet, requiredColumns || []);
  const updates = rows.map(function(row) {
    return {
      rowNumber: row._rowNumber,
      row: headers.map(function(header) {
        const value = row[header];
        return value === undefined || value === null ? "" : value;
      })
    };
  });
  writeUpdateRows_(sheet, updates, headers.length);
}

function ensureColumnsPresent_(sheet, requiredColumns) {
  const existingHeaders = getSheetHeaders_(sheet);
  if (existingHeaders.length === 0) {
    sheet.appendRow(requiredColumns);
    return requiredColumns.slice();
  }
  const missingColumns = requiredColumns.filter(function(column) {
    return existingHeaders.indexOf(column) === -1;
  });
  if (missingColumns.length === 0) {
    return existingHeaders;
  }
  const expandedHeaders = existingHeaders.concat(missingColumns);
  ensureSheetHasColumns_(sheet, expandedHeaders.length);
  sheet.getRange(1, 1, 1, expandedHeaders.length).setValues([expandedHeaders]);
  return expandedHeaders;
}

function ensureSheetHasColumns_(sheet, requiredLastColumn) {
  const currentMaxColumns = sheet.getMaxColumns();
  if (requiredLastColumn <= currentMaxColumns) {
    return;
  }
  sheet.insertColumnsAfter(currentMaxColumns, requiredLastColumn - currentMaxColumns);
}

function appendObjectsToSheet_(sheet, rows, orderedColumns) {
  ensureHeader_(sheet, orderedColumns);
  appendRows_(sheet, rows.map(function(row) {
    return orderedColumns.map(function(column) {
      const value = row[column];
      return value === undefined || value === null ? "" : value;
    });
  }), orderedColumns.length);
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
  const matchingRowNumbers = rows.filter(function(item) {
    return rowMatchesTestBatch_(item, testBatchId);
  }).map(function(item) {
    return item._rowNumber;
  });
  const deletionBlocks = buildDescendingRowDeletionBlocks_(matchingRowNumbers);

  if (!dryRun) {
    deletionBlocks.forEach(function(block) {
      sheet.deleteRows(block.start_row, block.row_count);
    });
    SpreadsheetApp.flush();
  }

  return {
    matched_rows: matchingRowNumbers.length,
    deleted_rows: dryRun ? 0 : matchingRowNumbers.length,
    deleted_blocks: dryRun ? 0 : deletionBlocks.length,
    remaining_rows: dryRun ? matchingRowNumbers.length : countRowsByTestBatch_(sheet, testBatchId)
  };
}

function buildDescendingRowDeletionBlocks_(rowNumbers) {
  if (!rowNumbers || rowNumbers.length === 0) {
    return [];
  }

  const sortedDescending = rowNumbers.slice().sort(function(left, right) {
    return right - left;
  });
  const blocks = [];
  let blockStart = sortedDescending[0];
  let blockCount = 1;

  for (var i = 1; i < sortedDescending.length; i++) {
    if (sortedDescending[i] === sortedDescending[i - 1] - 1) {
      blockStart = sortedDescending[i];
      blockCount += 1;
      continue;
    }

    blocks.push({ start_row: blockStart, row_count: blockCount });
    blockStart = sortedDescending[i];
    blockCount = 1;
  }

  blocks.push({ start_row: blockStart, row_count: blockCount });
  return blocks.sort(function(left, right) {
    return right.start_row - left.start_row;
  });
}

function countRowsByTestBatch_(sheet, testBatchId) {
  return getSheetRows_(sheet).filter(function(row) {
    return rowMatchesTestBatch_(row, testBatchId);
  }).length;
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

function upsertManyByKey_(sheet, keyColumns, payloads, orderedColumns) {
  ensureHeader_(sheet, orderedColumns);
  if (!payloads || payloads.length === 0) {
    return { inserted: 0, updated: 0, total: 0 };
  }

  const indexMap = getIndexMap_(sheet, keyColumns, orderedColumns);
  const updates = [];
  const inserts = [];
  let inserted = 0;
  let updated = 0;

  payloads.forEach(function(payload) {
    const key = buildCompositeKey_(payload, keyColumns);
    const row = orderedColumns.map(function(column) {
      const value = payload[column];
      return value === undefined || value === null ? "" : value;
    });

    if (indexMap[key]) {
      updates.push({ rowNumber: indexMap[key], row: row });
      updated += 1;
      return;
    }

    inserts.push(row);
    inserted += 1;
  });

  writeUpdateRows_(sheet, updates, orderedColumns.length);
  appendRows_(sheet, inserts, orderedColumns.length);
  return { inserted: inserted, updated: updated, total: payloads.length };
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

function writeUpdateRows_(sheet, updates, totalColumns) {
  if (!updates || updates.length === 0) {
    return;
  }

  updates.sort(function(left, right) {
    return left.rowNumber - right.rowNumber;
  });

  let groupStart = 0;
  while (groupStart < updates.length) {
    const grouped = [updates[groupStart]];
    let cursor = groupStart + 1;
    while (cursor < updates.length && updates[cursor].rowNumber === updates[cursor - 1].rowNumber + 1) {
      grouped.push(updates[cursor]);
      cursor += 1;
    }

    sheet
      .getRange(grouped[0].rowNumber, 1, grouped.length, totalColumns)
      .setValues(grouped.map(function(item) { return item.row; }));
    groupStart = cursor;
  }
}

function appendRows_(sheet, rows, totalColumns) {
  if (!rows || rows.length === 0) {
    return;
  }

  const startRow = Math.max(sheet.getLastRow(), 1) + 1;
  ensureSheetHasRows_(sheet, startRow + rows.length - 1);
  sheet.getRange(startRow, 1, rows.length, totalColumns).setValues(rows);
}

function ensureSheetHasRows_(sheet, requiredLastRow) {
  const currentMaxRows = sheet.getMaxRows();
  if (requiredLastRow <= currentMaxRows) {
    return;
  }
  sheet.insertRowsAfter(currentMaxRows, requiredLastRow - currentMaxRows);
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
