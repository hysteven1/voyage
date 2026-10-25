{{- define "voyage.name" -}}
{{- default (printf "%s-voyage" .Release.Name) .Values.fullnameOverride | trunc 50 | trimSuffix "-" -}}
{{- end -}}
{{- define "voyage.labels" -}}
app.kubernetes.io/name: voyage
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | quote }}
{{- end -}}
{{- define "voyage.image" -}}
{{- if .digest -}}
{{ .repository }}@{{ .digest }}
{{- else -}}
{{ .repository }}:{{ required "Set each images.<service>.tag to an immutable revision or provide a digest" .tag }}
{{- end -}}
{{- end -}}
{{- define "voyage.security" -}}
allowPrivilegeEscalation: false
readOnlyRootFilesystem: true
capabilities:
  drop: [ALL]
{{- end -}}
