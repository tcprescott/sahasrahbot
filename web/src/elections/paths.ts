/** Election page URLs. The vote and results links are also in SahasrahBot's Discord posts. */
export const votePath = (id: number) => `/ranked_choice/${id}`
export const editPath = (id: number) => `/elections/${id}/edit`
export const resultsPath = (id: number) => `/elections/${id}/results`
