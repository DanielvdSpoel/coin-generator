{{/*
Common labels for resources owned by the umbrella chart itself.
*/}}
{{- define "coin.labels" -}}
app.kubernetes.io/name: coin-generator
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end }}

{{/*
Service names created by the web-service subcharts. The subchart's fullname is
"<release>-<nameOverride>" (nameOverride is set per alias in values.yaml).
*/}}
{{- define "coin.apiService" -}}
{{ .Release.Name }}-{{ .Values.backend.nameOverride }}
{{- end }}

{{- define "coin.webService" -}}
{{ .Release.Name }}-{{ .Values.frontend.nameOverride }}
{{- end }}
